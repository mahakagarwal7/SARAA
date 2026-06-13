import json
import asyncio
# Force uvicorn reload to clear deadlocked threads
from typing import Dict, Any, List
from .base_agent import BaseAgent
from .research_agent import ResearchAgent
from .briefing_agent import BriefingAgent
from .writer_agent import WriterAgent
from .email_agent import EmailAgent
from .knowledge_agent import KnowledgeAgent
from utils.memory_db import MemoryDB

# Global in-memory cache for document context
DOCUMENT_CACHE: Dict[str, str] = {}

# We will import the real one later, but use a mock for now if needed
# from .scheduler_agent import SchedulerAgent 

class MockSchedulerAgent(BaseAgent):
    """Mock scheduler for testing when Graph API is unavailable."""
    def __init__(self):
        super().__init__(name="MockScheduler", role="Mock Calendar")
    async def execute(self, task):
        self.log_action("Using Mock Scheduler (Graph API unavailable)")
        return {
            "status": "success",
            "action": "check_calendar",
            "data": [
                {"subject": "Team Standup", "start": "2026-06-10T09:00:00"},
                {"subject": "Lunch with Sarah", "start": "2026-06-10T12:30:00"}
            ]
        }

class OrchestratorAgent(BaseAgent):
    """The central brain that coordinates the agent swarm."""
    
    def __init__(self, use_mock_scheduler: bool = False, access_token: str = None, user_id: str = "user_123"):
        super().__init__(name="Orchestrator", role="Swarm Coordinator")
        self.use_mock_scheduler = use_mock_scheduler
        self.access_token = access_token
        self.user_id = user_id
        self.research_agent = ResearchAgent()
        self.briefing_agent = BriefingAgent()
        self.writer_agent = WriterAgent()
        self.email_agent = EmailAgent(access_token=access_token)
        self.knowledge_agent = KnowledgeAgent()
        self.memory = MemoryDB()
        
        # Use Mock if Graph API isn't ready, otherwise use Real
        if use_mock_scheduler:
            self.scheduler_agent = MockSchedulerAgent()
            self.log_action("⚠️ Orchestrator initialized with MOCK Scheduler")
        else:
            from .scheduler_agent import SchedulerAgent
            self.scheduler_agent = SchedulerAgent(access_token=access_token)
            self.log_action("✅ Orchestrator initialized with REAL Graph Scheduler")

    async def execute(self, user_request: str, image_base64: str = None, file_name: str = None, file_base64: str = None, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Main entry point for the swarm."""
        self.log_action(f"Received user request: '{user_request}'")
        
        if image_base64:
            self.log_action("Analyzing attached image...")
            image_description = await self._analyze_image(image_base64, user_request)
            user_request = f"{user_request}\n\n[ATTACHED IMAGE DESCRIPTION: {image_description}]"
            
        if file_base64 and file_name:
            self.log_action(f"Extracting text from attached document: {file_name}...")
            file_text = await self._extract_text_from_file(file_base64, file_name)
            user_request = f"{user_request}\n\n[ATTACHED DOCUMENT '{file_name}' CONTENTS:\n{file_text}]"
            
            # Index document into Knowledge Base
            self.log_action(f"Indexing document '{file_name}' into Knowledge Base...")
            await self.knowledge_agent.execute({
                "action": "add_document",
                "doc_id": file_name,
                "text": file_text,
                "metadata": {"user_id": self.user_id}
            })
        
        if not self.use_mock_scheduler:
            self.log_action("Running True AutoGen Swarm (Production Mode)...")
            return await self._run_autogen_swarm(user_request, chat_history)
            
        self.log_action("Running Sequential Swarm (Mock Mode)...")
        
        # Format chat history into the prompt for the decompose planner
        context_prefix = ""
        if chat_history:
            history_text = "\n\n".join([f"**{msg.get('role', 'unknown').upper()}**:\n{msg.get('content', '')}" for msg in chat_history[-3:]])
            context_prefix = f"--- PREVIOUS CONVERSATION HISTORY (Last 3 messages) ---\n{history_text}\n--- END HISTORY ---\n\n"
            
        full_request = context_prefix + user_request

        # 1. Decompose the request into a plan
        plan = await self._decompose_request(full_request)
        self.log_action(f"Execution Plan: {json.dumps(plan, indent=2)}")
        
        execution_log = []
        results = {}
        
        # 2. Execute Research Tasks
        if plan.get("needs_research", False):
            self.log_action("Dispatching to Research Agent...")
            research_task = {"query": plan.get("research_query", user_request), "num_results": 3}
            research_result = await self.research_agent.execute(research_task)
            results["research"] = research_result
            execution_log.append({"agent": "ResearchAgent", "status": research_result["status"]})
        
        # 3. Execute Scheduling Tasks
        if plan.get("needs_calendar", False):
            self.log_action("Dispatching to Scheduler Agent...")
            calendar_task = {"action": "check_calendar"}
            calendar_result = await self.scheduler_agent.execute(calendar_task)
            results["calendar"] = calendar_result
            execution_log.append({"agent": "SchedulerAgent", "status": calendar_result["status"]})
        
        # 4. Generate Briefing
        if plan.get("needs_briefing", False) and results.get("research"):
            self.log_action("Dispatching to Briefing Agent...")
            calendar_data = results.get("calendar", {}).get("data", [])
            briefing_task = {
                "meeting_subject": plan.get("meeting_subject", "Executive Meeting"),
                "research_synthesis": results["research"].get("synthesis", ""),
                "calendar_context": str(calendar_data) if calendar_data else "No calendar context required/provided."
            }
            briefing_result = await self.briefing_agent.execute(briefing_task)
            results["briefing"] = briefing_result
            execution_log.append({"agent": "BriefingAgent", "status": briefing_result["status"]})
        
        # 5. Compile Final Response
        if plan.get("needs_writer", False) and results.get("briefing"):
            self.log_action("Dispatching to Writer Agent...")
            writer_task = {
                "briefing_markdown": results["briefing"].get("briefing_markdown", ""),
                "user_request": user_request,
                "document_type": plan.get("document_type", "document")
            }
            writer_result = await self.writer_agent.execute(writer_task)
            results["writer"] = writer_result
            execution_log.append({"agent": "WriterAgent", "status": writer_result["status"]})

        # 6. Compile Final Response
        final_summary = await self._compile_summary(user_request, results)
        
        return {
            "status": "success",
            "execution_log": execution_log,
            "results": results,
            "final_summary": final_summary
        }

    async def execute_stream(self, user_request: str, image_base64: str = None, file_name: str = None, file_base64: str = None, chat_history: List[Dict[str, str]] = None):
        """Async generator that yields SSE JSON strings."""
        try:
            yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Received user request..."})
            await asyncio.sleep(0.1)
            
            if image_base64:
                yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Analyzing attached image..."})
                image_description = await self._analyze_image(image_base64, user_request)
                user_request = f"{user_request}\n\n[ATTACHED IMAGE DESCRIPTION: {image_description}]"

            if file_base64 and file_name:
                yield json.dumps({"type": "log", "agent": "Orchestrator", "status": f"Reading document {file_name}..."})
                file_text = await self._extract_text_from_file(file_base64, file_name)
                doc_context = f"[ATTACHED DOCUMENT '{file_name}' CONTENTS:\n{file_text}]"
                DOCUMENT_CACHE[self.user_id] = doc_context
                user_request = f"{user_request}\n\n{doc_context}"
                
                yield json.dumps({"type": "log", "agent": "KnowledgeAgent", "status": f"Indexing {file_name} into Knowledge Base..."})
                await self.knowledge_agent.execute({
                    "action": "add_document",
                    "doc_id": file_name,
                    "text": file_text,
                    "metadata": {"user_id": self.user_id}
                })
            elif self.user_id in DOCUMENT_CACHE:
                # If there is a cached document, append it so follow-up questions have context
                user_request = f"{user_request}\n\n[CONTEXT FROM PREVIOUSLY ATTACHED DOCUMENT:]\n{DOCUMENT_CACHE[self.user_id]}"

            if not self.use_mock_scheduler:
                yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Initializing AutoGen Swarm..."})
                await asyncio.sleep(0.5)
                
                import sys
                import contextlib
                import re
                
                queue = asyncio.Queue()
                loop = asyncio.get_running_loop()
                
                class QueueStream:
                    def __init__(self):
                        self.buffer = ""
                        
                    def write(self, text):
                        # Remove ANSI escape codes
                        clean_text = re.sub(r'\x1b\[[0-9;]*m', '', text)
                        self.buffer += clean_text
                        
                        if '\n' in self.buffer:
                            lines = self.buffer.split('\n')
                            # Emit all complete lines
                            for line in lines[:-1]:
                                if line.strip():
                                    loop.call_soon_threadsafe(queue.put_nowait, line)
                            # Keep remainder
                            self.buffer = lines[-1]
                            
                    def flush(self):
                        if self.buffer.strip():
                            loop.call_soon_threadsafe(queue.put_nowait, self.buffer)
                            self.buffer = ""
                        
                stream = QueueStream()
                
                # Run the swarm in a completely separate thread because AutoGen's underlying 
                # LLM client uses synchronous requests that block the FastAPI event loop.
                async def run_swarm():
                    def _sync_wrapper():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                                return new_loop.run_until_complete(self._run_autogen_swarm(user_request, chat_history))
                        finally:
                            new_loop.close()
                    return await asyncio.to_thread(_sync_wrapper)
                        
                task = asyncio.create_task(run_swarm())
                
                yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Swarm deployed. Waiting for agents..."})
                
                while not task.done():
                    try:
                        line = await asyncio.wait_for(queue.get(), timeout=5.0)
                        if " (to " in line:
                            agent = line.split(" (to ")[0].strip()
                            yield json.dumps({"type": "log", "agent": agent, "status": "Drafting response..."})
                        elif "Suggested function call:" in line:
                            yield json.dumps({"type": "log", "agent": "System", "status": "Invoking Tool Execution..."})
                        elif "TERMINATE" in line:
                            yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Swarm reached consensus. Finalizing..."})
                        elif "🚨" in line or "ACTION REQUIRED" in line:
                            yield json.dumps({"type": "log", "agent": "System", "status": line.strip()})
                        elif "Error" in line or "Exception" in line or "RateLimit" in line:
                            yield json.dumps({"type": "log", "agent": "System", "status": f"Warning: {line[:100]}..."})
                    except asyncio.TimeoutError:
                        yield json.dumps({"type": "keep-alive"})
                        continue
                
                # Drain queue
                while not queue.empty():
                    queue.get_nowait()
                    
                try:
                    result = task.result()
                    yield json.dumps({"type": "result", "data": result})
                except Exception as e:
                    self.log_action(f"Agent execution failed: {e}", level="ERROR")
                    yield json.dumps({"type": "log", "agent": "Orchestrator", "status": f"Agent execution failed: {str(e)}"})
                    yield json.dumps({"type": "result", "data": {"status": "error", "message": str(e), "execution_log": [{"agent": "Orchestrator", "status": "error"}], "results": {}, "final_summary": f"Agent execution failed: {str(e)}"}})
                return

            # Format chat history into the prompt
            context_prefix = ""
            if chat_history:
                history_text = "\n\n".join([f"**{msg.get('role', 'unknown').upper()}**:\n{msg.get('content', '')}" for msg in chat_history[-3:]]) # Keep last 3 to save tokens
                context_prefix = f"--- PREVIOUS CONVERSATION HISTORY ---\n{history_text}\n--- END HISTORY ---\n\n"
                
            full_request = context_prefix + user_request

            yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Decomposing task into sub-agent plan..."})
            plan = await self._decompose_request(full_request)
            await asyncio.sleep(0.5)

            results = {}
            execution_log = []

            if plan.get("needs_research", False):
                yield json.dumps({"type": "log", "agent": "ResearchAgent", "status": "Searching the web for latest information..."})
                await asyncio.sleep(1.5)
                research_task = {"query": plan.get("research_query", user_request), "num_results": 3}
                results["research"] = await self.research_agent.execute(research_task)
                execution_log.append({"agent": "ResearchAgent", "status": "success"})
                yield json.dumps({"type": "log", "agent": "ResearchAgent", "status": "Research complete."})

            if plan.get("needs_calendar", False):
                yield json.dumps({"type": "log", "agent": "SchedulerAgent", "status": "Connecting to Microsoft Graph to check calendar..."})
                await asyncio.sleep(1.5)
                calendar_task = {"action": "check_calendar"}
                results["calendar"] = await self.scheduler_agent.execute(calendar_task)
                execution_log.append({"agent": "SchedulerAgent", "status": "success"})
                yield json.dumps({"type": "log", "agent": "SchedulerAgent", "status": "Calendar check complete."})

            if plan.get("needs_briefing", False) and results.get("research"):
                yield json.dumps({"type": "log", "agent": "BriefingAgent", "status": "Synthesizing research into executive briefing..."})
                await asyncio.sleep(2)
                calendar_data = results.get("calendar", {}).get("data", [])
                briefing_task = {
                    "meeting_subject": plan.get("meeting_subject", "Executive Meeting"),
                    "research_synthesis": results["research"].get("synthesis", ""),
                    "calendar_context": str(calendar_data) if calendar_data else "No calendar context required/provided."
                }
                results["briefing"] = await self.briefing_agent.execute(briefing_task)
                execution_log.append({"agent": "BriefingAgent", "status": "success"})
                yield json.dumps({"type": "log", "agent": "BriefingAgent", "status": "Briefing document generated."})

            if plan.get("needs_writer", False) and results.get("briefing"):
                yield json.dumps({"type": "log", "agent": "WriterAgent", "status": f"Drafting {plan.get('document_type', 'document')}..."})
                await asyncio.sleep(2)
                writer_task = {
                    "briefing_markdown": results["briefing"].get("briefing_markdown", ""),
                    "user_request": user_request,
                    "document_type": plan.get("document_type", "document")
                }
                results["writer"] = await self.writer_agent.execute(writer_task)
                execution_log.append({"agent": "WriterAgent", "status": "success"})
                yield json.dumps({"type": "log", "agent": "WriterAgent", "status": "Document draft generated."})

            yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Compiling final summary..."})
            final_summary = await self._compile_summary(user_request, results)
            await asyncio.sleep(1)

            final_result = {
                "status": "success",
                "execution_log": execution_log,
                "results": results,
                "final_summary": final_summary
            }
            yield json.dumps({"type": "result", "data": final_result})

        except Exception as e:
            self.log_action(f"Agent stream crashed: {e}", level="ERROR")
            yield json.dumps({"type": "log", "agent": "Orchestrator", "status": f"System error: {str(e)}"})
            yield json.dumps({"type": "result", "data": {"status": "error", "message": str(e), "execution_log": [{"agent": "Orchestrator", "status": "error"}], "results": {}, "final_summary": f"System error: {str(e)}"}})

    async def _run_autogen_swarm(self, user_request: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Run the AutoGen GroupChat for dynamic orchestration."""
        import os
        os.environ["AUTOGEN_USE_DOCKER"] = "False"
        
        import autogen
        from utils.config import settings
        from tools.autogen_tools import perform_research, check_calendar, generate_briefing, draft_document, fetch_unread_emails, draft_email_reply, query_knowledge_base, set_access_token
        
        # Set access token for tools that require authentication
        set_access_token(self.access_token)
        
        # Fetch user preferences
        prefs = self.memory.get_preferences(self.user_id)
        prefs_text = ", ".join([f"{k}: {v}" for k, v in prefs.items()]) if prefs else "None"

        # Configure LLM for AutoGen
        llm_config = {
            "config_list": [{
                "model": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                "api_key": settings.AZURE_OPENAI_API_KEY,
                "base_url": f"{settings.AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}",
                "api_type": "openai",
                "default_query": {"api-version": settings.AZURE_OPENAI_API_VERSION},
                "default_headers": {"api-key": settings.AZURE_OPENAI_API_KEY}
            }],
            "temperature": 0.2,
            "cache_seed": None
        }

        # Initialize Agents
        user_proxy = autogen.UserProxyAgent(
            name="Executive",
            system_message=f"An executive requesting assistance. Execute functions when suggested. User preferences: {prefs_text}. When you provide the final answer, keep your own thinking/process points very brief and focus on giving the relevant details properly. CRITICAL: DO NOT output any internal thinking processes, <think> tags, or conversational filler. Avoid literal `\\n` strings.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config=False
        )
        
        researcher = autogen.AssistantAgent(
            name="Researcher",
            system_message=f"You are a research agent. Use the perform_research tool to find information. If a query is location-dependent (like weather) and the user didn't specify a location, use the location from these User Preferences: {prefs_text}. When summarizing findings, keep process explanations short and focus on actual details. CRITICAL: DO NOT output any internal thinking processes, <think> tags, or conversational filler. Avoid literal `\\n` strings.",
            llm_config=llm_config
        )
        
        scheduler = autogen.AssistantAgent(
            name="Scheduler",
            system_message="You are a scheduling agent. Use the check_calendar tool to find calendar conflicts.",
            llm_config=llm_config
        )
        
        briefer = autogen.AssistantAgent(
            name="Briefer",
            system_message="You are a briefing agent. Use the generate_briefing tool to create a briefing document once research and scheduling are done.",
            llm_config=llm_config
        )

        writer = autogen.AssistantAgent(
            name="Writer",
            system_message="You are a writer agent. Use the draft_document tool to write documents, reports, outlines, emails, or memos ONLY IF the user explicitly asked for a document/draft. If the user did not explicitly ask for a draft/email/document/outline, you MUST NOT use the draft_document tool. In that case, output TERMINATE immediately. CRITICAL: DO NOT output any internal thinking processes, <think> tags, or conversational filler. Avoid literal `\\n` strings.",
            llm_config=llm_config
        )
        
        emailer = autogen.AssistantAgent(
            name="Emailer",
            system_message="You are an email agent. Use the fetch_unread_emails tool to check the inbox. Use draft_email_reply to reply to threads. CRITICAL: DO NOT output any internal thinking processes, <think> tags, or conversational filler.",
            llm_config=llm_config
        )
        
        knowledge = autogen.AssistantAgent(
            name="Knowledge",
            system_message="You are a knowledge retriever. Use the query_knowledge_base tool to find information from previously saved documents. CRITICAL: DO NOT output any internal thinking processes, <think> tags, or conversational filler.",
            llm_config=llm_config
        )
        
        # Register tools
        autogen.agentchat.register_function(
            perform_research,
            caller=researcher,
            executor=user_proxy,
            description="Perform web research on a specific query."
        )
        
        autogen.agentchat.register_function(
            check_calendar,
            caller=scheduler,
            executor=user_proxy,
            description="Check the executive's calendar."
        )
        
        autogen.agentchat.register_function(
            generate_briefing,
            caller=briefer,
            executor=user_proxy,
            description="Generate a briefing document based on research and calendar."
        )
        
        autogen.agentchat.register_function(
            draft_document,
            caller=writer,
            executor=user_proxy,
            description="Draft a document (report/outline/email/memo) based on the briefing and user request."
        )
        
        autogen.agentchat.register_function(
            fetch_unread_emails,
            caller=emailer,
            executor=user_proxy,
            description="Fetch unread emails from the executive's Outlook Inbox."
        )
        
        autogen.agentchat.register_function(
            draft_email_reply,
            caller=emailer,
            executor=user_proxy,
            description="Draft a reply to a specific email thread."
        )
        
        autogen.agentchat.register_function(
            query_knowledge_base,
            caller=knowledge,
            executor=user_proxy,
            description="Query the personal knowledge base (RAG) for information from previously uploaded documents."
        )
        
        # Create GroupChat
        groupchat = autogen.GroupChat(
            agents=[user_proxy, researcher, scheduler, briefer, writer, emailer, knowledge],
            messages=[],
            max_round=6
        )
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
        
        # Format chat history into the prompt (Limit to last 2 messages to prevent token limits)
        context_prefix = ""
        if chat_history:
            recent_history = chat_history[-2:] if len(chat_history) > 2 else chat_history
            history_text = "\n\n".join([f"**{msg.get('role', 'unknown').upper()}**:\n{msg.get('content', '')}" for msg in recent_history])
            context_prefix = f"--- PREVIOUS CONVERSATION HISTORY (Last {len(recent_history)} messages) ---\n{history_text}\n--- END HISTORY ---\n\nPLEASE FULFILL THIS NEW REQUEST CONTINUING FROM THE CONTEXT ABOVE:\n\n"
            
        full_request = context_prefix + user_request
        
        # Initiate Chat (AutoGen a_initiate_chat supports async)
        chat_res = await user_proxy.a_initiate_chat(
            manager,
            message=full_request,
            summary_method="last_msg"
        )
        
        # AutoGen's last_msg often just returns the raw JSON from the final tool execution.
        # Skip the first message as it contains the full previous chat history string,
        # which can confuse the compiler into repeating previous outputs.
        new_messages = chat_res.chat_history[1:] if len(chat_res.chat_history) > 1 else chat_res.chat_history
        final_summary = await self._compile_summary(user_request, {"chat_history": new_messages})
            
        # Extract the actual generated documents from the chat history so the frontend can display them
        combined_markdown = ""
        import ast
        for msg in chat_res.chat_history:
            content = msg.get("content", "")
            if not isinstance(content, str):
                continue
            
            # Try to parse the content as a dict (either JSON or Python string representation)
            data = {}
            try:
                data = json.loads(content)
            except Exception:
                try:
                    data = ast.literal_eval(content)
                except Exception:
                    pass
                    
            if isinstance(data, dict):
                if "briefing_markdown" in data:
                    combined_markdown += f"\n\n## Briefing\n\n{data['briefing_markdown']}"
                if "draft_document" in data:
                    doc_type = data.get("document_type", "Document").title()
                    combined_markdown += f"\n\n## {doc_type}\n\n{data['draft_document']}"
        
        results = {"chat_history": chat_res.chat_history}
        if combined_markdown:
            # The frontend specifically looks for `results.briefing.briefing_markdown` to display the document
            results["briefing"] = {"briefing_markdown": combined_markdown.strip()}
        
        return {
            "status": "success",
            "execution_log": [{"agent": "AutoGenManager", "status": "success"}],
            "results": results,
            "final_summary": final_summary
        }

    async def _extract_text_from_file(self, file_base64: str, file_name: str) -> str:
        """Extract text from PDF or DOCX file."""
        import base64
        import io
        try:
            file_bytes = base64.b64decode(file_base64)
            extracted_text = ""
            
            if file_name.lower().endswith('.pdf'):
                import pypdf
                reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                for page in reader.pages:
                    extracted_text += page.extract_text() + "\n"
            elif file_name.lower().endswith(('.docx', '.doc')):
                import docx
                doc = docx.Document(io.BytesIO(file_bytes))
                for para in doc.paragraphs:
                    extracted_text += para.text + "\n"
            else:
                return f"[Unsupported file type: {file_name}]"
                
            # Truncate to prevent token limits and WAF payload drops
            max_chars = 15000
            if len(extracted_text) > max_chars:
                extracted_text = extracted_text[:max_chars] + f"\n\n[TEXT TRUNCATED AT {max_chars} CHARACTERS]"
                
            return extracted_text.strip()
        except Exception as e:
            self.log_action(f"File extraction failed: {e}", level="ERROR")
            return f"[File extraction failed: {str(e)}]"

    async def _analyze_image(self, image_base64: str, prompt: str) -> str:
        """Analyze an uploaded image using the Vision model."""
        try:
            from azure.ai.inference.models import SystemMessage, UserMessage, TextContentItem, ImageContentItem, ImageUrl
            messages = [
                SystemMessage(content="You are an expert executive assistant with advanced vision capabilities. The user has provided an image along with their request. Thoroughly describe the image, extracting any text, numbers, charts, or context that might be relevant to the user's prompt."),
                UserMessage(content=[
                    TextContentItem(text=f"Please analyze this image in the context of my request: {prompt}"),
                    ImageContentItem(image_url=ImageUrl(url=f"data:image/jpeg;base64,{image_base64}"))
                ])
            ]
            return self._call_llm(messages, temperature=0.2)
        except Exception as e:
            self.log_action(f"Image analysis failed: {e}", level="ERROR")
            return f"[Image analysis failed: {str(e)}]"

    async def _decompose_request(self, user_request: str) -> Dict[str, Any]:
        """Use LLM to break down the user prompt into a structured JSON plan."""
        # Fetch user preferences from MemoryDB (using the real user ID)
        prefs = self.memory.get_preferences(self.user_id)
        prefs_text = "\\n".join([f"- {k}: {v}" for k, v in prefs.items()]) if prefs else "None"
        
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""
        Analyze this executive request and output a JSON plan.
        Current Date Context: {current_date}
        
        USER PREFERENCES:
        {prefs_text}
        
        REQUEST: "{user_request}"
        
        Output ONLY valid JSON with this exact structure:
        {{
            "needs_research": true/false,
            "research_query": "specific search query if needed. Be sure to include the current year ({current_date[:4]}) if the query implies an upcoming or current event.",
            "needs_calendar": true/false,
            "needs_briefing": true/false,
            "meeting_subject": "name of meeting if applicable",
            "needs_writer": true/false (ONLY set to true if the user EXPLICITLY asks to draft, write, or send an email/document/memo. Otherwise, strictly false),
            "document_type": "email, memo, or announcement if applicable"
        }}
        """
        
        messages = self._build_messages(
            system_prompt="You are a task planner. Output ONLY valid JSON. No markdown formatting.",
            user_message=prompt
        )
        
        raw_json = self._call_llm(messages, temperature=0.2)
        
        # Clean up JSON (remove markdown code blocks if LLM adds them)
        raw_json = raw_json.replace("```json", "").replace("```", "").strip()
        
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            self.log_action("JSON parsing failed. Using fallback plan.", level="ERROR")
            return {
                "needs_research": True,
                "research_query": user_request,
                "needs_calendar": True,
                "needs_briefing": True,
                "meeting_subject": "General Meeting",
                "needs_writer": False,
                "document_type": ""
            }

    async def _compile_summary(self, original_request: str, results: Dict) -> str:
        """Generate a final human-readable summary of what the swarm did."""
        prompt = f"""
        The user asked: "{original_request}"
        
        Here are the raw results from the agent swarm:
        {json.dumps(results, indent=2, default=str)[:10000]}
        
        Your task is to present this information back to the user in a beautifully formatted, highly professional Markdown response.
        
        CRITICAL RULES:
        1. ABSOLUTELY NO JSON. Do not output any curly braces {{}}, "status": "success", or JSON-like syntax. 
        2. BE POLISHED & PROFESSIONAL. Act as a world-class Executive Assistant. Start with a polite, brief conversational opening (e.g., "I have completed the requested task. Here are the details:"). 
        3. FULL DETAILS. If the agents drafted a document, memo, or briefing, you MUST output the full text of those documents. Do not summarize them away. Use Markdown headers (##) to separate different documents or sections cleanly.
        4. Do not include internal process explanations or "thinking" tags. Make the output look like a final, polished deliverable ready for an executive to read.
        """
        
        messages = self._build_messages(
            system_prompt="You are an executive assistant summarizing completed tasks.",
            user_message=prompt
        )
        
        return self._call_llm(messages, temperature=0.3)