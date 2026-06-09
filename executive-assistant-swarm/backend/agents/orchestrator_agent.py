import json
from typing import Dict, Any, List
from .base_agent import BaseAgent
from .research_agent import ResearchAgent
from .briefing_agent import BriefingAgent

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
    
    def __init__(self, use_mock_scheduler: bool = False):
        super().__init__(name="Orchestrator", role="Swarm Coordinator")
        self.research_agent = ResearchAgent()
        self.briefing_agent = BriefingAgent()
        
        # Use Mock if Graph API isn't ready, otherwise use Real
        if use_mock_scheduler:
            self.scheduler_agent = MockSchedulerAgent()
            self.log_action("⚠️ Orchestrator initialized with MOCK Scheduler")
        else:
            from .scheduler_agent import SchedulerAgent
            self.scheduler_agent = SchedulerAgent()
            self.log_action("✅ Orchestrator initialized with REAL Graph Scheduler")

    async def execute(self, user_request: str) -> Dict[str, Any]:
        """Main entry point for the swarm."""
        self.log_action(f"Received user request: '{user_request}'")
        
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
        
        # 4. Generate Briefing (if both research and calendar are done)
        if plan.get("needs_briefing", False) and results.get("research") and results.get("calendar"):
            self.log_action("Dispatching to Briefing Agent...")
            briefing_task = {
                "meeting_subject": plan.get("meeting_subject", "Executive Meeting"),
                "research_synthesis": results["research"].get("synthesis", ""),
                "calendar_context": str(results["calendar"].get("data", []))
            }
            briefing_result = await self.briefing_agent.execute(briefing_task)
            results["briefing"] = briefing_result
            execution_log.append({"agent": "BriefingAgent", "status": briefing_result["status"]})
        
        # 5. Compile Final Response
        final_summary = await self._compile_summary(user_request, results)
        
        return {
            "status": "success",
            "execution_log": execution_log,
            "results": results,
            "final_summary": final_summary
        }

    async def _decompose_request(self, user_request: str) -> Dict[str, Any]:
        """Use LLM to break down the user prompt into a structured JSON plan."""
        prompt = f"""
        Analyze this executive request and output a JSON plan.
        
        REQUEST: "{user_request}"
        
        Output ONLY valid JSON with this exact structure:
        {{
            "needs_research": true/false,
            "research_query": "specific search query if needed",
            "needs_calendar": true/false,
            "needs_briefing": true/false,
            "meeting_subject": "name of meeting if applicable"
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
                "meeting_subject": "General Meeting"
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