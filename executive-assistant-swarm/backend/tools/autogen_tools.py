import asyncio
from typing import Dict, Any

async def perform_research(query: str, num_results: int = 3) -> Dict[str, Any]:
    """Perform web research on a specific query."""
    from agents.research_agent import ResearchAgent
    agent = ResearchAgent()
    return await agent.execute({"query": query, "num_results": num_results})

async def check_calendar() -> Dict[str, Any]:
    """Check the executive's calendar for upcoming events and conflicts."""
    from agents.scheduler_agent import SchedulerAgent
    agent = SchedulerAgent()
    return await agent.execute({"action": "check_calendar"})

async def generate_briefing(meeting_subject: str, research_synthesis: str, calendar_context: str) -> Dict[str, Any]:
    """Generate a briefing document and presentation outline based on research and calendar data."""
    from agents.briefing_agent import BriefingAgent
    agent = BriefingAgent()
    return await agent.execute({
        "meeting_subject": meeting_subject,
        "research_synthesis": research_synthesis,
        "calendar_context": calendar_context
    })
