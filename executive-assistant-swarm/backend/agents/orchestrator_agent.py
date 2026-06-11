import json
import asyncio
from typing import Dict, Any, List
from .base_agent import BaseAgent
from .research_agent import ResearchAgent
from .briefing_agent import BriefingAgent
from .writer_agent import WriterAgent
from utils.memory_db import MemoryDB

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
        self.memory = MemoryDB()
        
        # Use Mock if Graph API isn't ready, otherwise use Real
        if use_mock_scheduler:
            self.scheduler_agent = MockSchedulerAgent()
            self.log_action("⚠️ Orchestrator initialized with MOCK Scheduler")
        else:
            from .scheduler_agent import SchedulerAgent
            self.scheduler_agent = SchedulerAgent(access_token=access_token)
            self.log_action("✅ Orchestrator initialized with REAL Graph Scheduler")

    async def execute(self, user_request: str) -> Dict[str, Any]:
        """Main entry point for the swarm."""
        self.log_action(f"Received user request: '{user_request}'")
        
        if not self.use_mock_scheduler:
            self.log_action("Running True AutoGen Swarm (Production Mode)...")
            return await self._run_autogen_swarm(user_request)
            
        self.log_action("Running Sequential Swarm (Mock Mode)...")
        # 1. Decompose the request into a plan
        plan = await self._decompose_request(user_request)
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

    async def execute_stream(self, user_request: str):
        """Async generator that yields SSE JSON strings."""
        yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Received user request..."})
        await asyncio.sleep(0.5)

        if not self.use_mock_scheduler:
            yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Initializing AutoGen Swarm..."})
            await asyncio.sleep(0.5)
            
            import sys
            import contextlib
            
            queue = asyncio.Queue()
            loop = asyncio.get_running_loop()
            
            class QueueStream:
                def write(self, text):
                    if text.strip():
                        # AutoGen prints synchronously, so we must schedule it on the event loop
                        loop.call_soon_threadsafe(queue.put_nowait, text)
                def flush(self):
                    pass
                    
            stream = QueueStream()
            
            # Run the swarm in a completely separate thread because AutoGen's underlying 
            # LLM client uses synchronous requests that block the FastAPI event loop.
            async def run_swarm():
                def _sync_wrapper():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        with contextlib.redirect_stdout(stream):
                            return new_loop.run_until_complete(self._run_autogen_swarm(user_request))
                    finally:
                        new_loop.close()
                return await asyncio.to_thread(_sync_wrapper)
                    
            task = asyncio.create_task(run_swarm())
            
            yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Swarm deployed. Waiting for agents..."})
            
            while not task.done():
                try:
                    line = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if " (to " in line:
                        agent = line.split(" (to ")[0].strip()
                        yield json.dumps({"type": "log", "agent": agent, "status": "Drafting response..."})
                    elif "Suggested function call:" in line:
                        yield json.dumps({"type": "log", "agent": "System", "status": "Invoking Tool Execution..."})
                    elif "TERMINATE" in line:
                        yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Swarm reached consensus. Finalizing..."})
                except asyncio.TimeoutError:
                    continue
            
            # Drain queue
            while not queue.empty():
                queue.get_nowait()
                
            result = task.result()
            yield json.dumps({"type": "result", "data": result})
            return

        yield json.dumps({"type": "log", "agent": "Orchestrator", "status": "Decomposing task into sub-agent plan..."})
        plan = await self._decompose_request(user_request)
        await asyncio.sleep(1)

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

    async def _run_autogen_swarm(self, user_request: str) -> Dict[str, Any]:
        """Run the AutoGen GroupChat for dynamic orchestration."""
        import os
        os.environ["AUTOGEN_USE_DOCKER"] = "False"
        
        import autogen
        from utils.config import settings
        from tools.autogen_tools import perform_research, check_calendar, generate_briefing, draft_document
        
        # Configure LLM for AutoGen
        llm_config = {
            "config_list": [{
                "model": settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                "api_key": settings.AZURE_OPENAI_API_KEY,
                "base_url": settings.AZURE_OPENAI_ENDPOINT,
                "api_type": "azure",
                "api_version": "2024-05-01-preview"
            }],
            "temperature": 0.2
        }

        # Initialize Agents
        user_proxy = autogen.UserProxyAgent(
            name="Executive",
            system_message="An executive requesting assistance. Execute functions when suggested.",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config=False
        )
        
        researcher = autogen.AssistantAgent(
            name="Researcher",
            system_message="You are a research agent. Use the perform_research tool to find information.",
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
            system_message="You are a writer agent. Use the draft_document tool to write follow-up emails, memos, or announcements based on the briefing. If a draft is generated or not needed, output TERMINATE.",
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
            description="Draft a document (email/memo/announcement) based on the briefing and user request."
        )
        
        # Create GroupChat
        groupchat = autogen.GroupChat(
            agents=[user_proxy, researcher, scheduler, briefer, writer],
            messages=[],
            max_round=12
        )
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
        
        # Initiate Chat (AutoGen a_initiate_chat supports async)
        chat_res = await user_proxy.a_initiate_chat(
            manager,
            message=user_request
        )
        
        final_summary = chat_res.summary if hasattr(chat_res, "summary") and chat_res.summary else "AutoGen Swarm completed the request."
        
        return {
            "status": "success",
            "execution_log": [{"agent": "AutoGenManager", "status": "success"}],
            "results": {"chat_history": chat_res.chat_history},
            "final_summary": final_summary
        }

    async def _decompose_request(self, user_request: str) -> Dict[str, Any]:
        """Use LLM to break down the user prompt into a structured JSON plan."""
        # Fetch user preferences from MemoryDB (using the real user ID)
        prefs = self.memory.get_preferences(self.user_id)
        prefs_text = "\\n".join([f"- {k}: {v}" for k, v in prefs.items()]) if prefs else "None"
        
        prompt = f"""
        Analyze this executive request and output a JSON plan.
        
        USER PREFERENCES:
        {prefs_text}
        
        REQUEST: "{user_request}"
        
        Output ONLY valid JSON with this exact structure:
        {{
            "needs_research": true/false,
            "research_query": "specific search query if needed",
            "needs_calendar": true/false,
            "needs_briefing": true/false,
            "meeting_subject": "name of meeting if applicable",
            "needs_writer": true/false,
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
        
        The agent swarm completed the following tasks:
        {json.dumps(results, indent=2, default=str)[:1500]}
        
        Write a 2-3 sentence summary for the user explaining what was accomplished and highlighting the most important finding.
        """
        
        messages = self._build_messages(
            system_prompt="You are an executive assistant summarizing completed tasks.",
            user_message=prompt
        )
        
        return self._call_llm(messages, temperature=0.3)