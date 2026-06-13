import asyncio
from typing import Dict, Any

_global_access_token = None

def set_access_token(token: str):
    global _global_access_token
    _global_access_token = token

async def perform_research(query: str, num_results: int = 3) -> Dict[str, Any]:
    """Perform web research on a specific query."""
    from agents.research_agent import ResearchAgent
    agent = ResearchAgent()
    return await agent.execute({"query": query, "num_results": num_results})

async def check_calendar() -> Dict[str, Any]:
    """Check the executive's calendar for upcoming events and conflicts."""
    from agents.scheduler_agent import SchedulerAgent
    agent = SchedulerAgent(access_token=_global_access_token)
    return await agent.execute({"action": "check_calendar"})

async def generate_briefing(meeting_subject: str, research_synthesis: str, calendar_context: str = "No calendar context provided.") -> Dict[str, Any]:
    """Generate a briefing document and presentation outline based on research and calendar data."""
    from agents.briefing_agent import BriefingAgent
    agent = BriefingAgent()
    return await agent.execute({
        "meeting_subject": meeting_subject,
        "research_synthesis": research_synthesis,
        "calendar_context": calendar_context
    })

async def draft_document(briefing_markdown: str, user_request: str, document_type: str = "document") -> Dict[str, Any]:
    """Draft a document, report, email, memo, or outline based on the briefing."""
    from agents.writer_agent import WriterAgent
    agent = WriterAgent()
    return await agent.execute({
        "briefing_markdown": briefing_markdown,
        "user_request": user_request,
        "document_type": document_type
    })

async def fetch_unread_emails(max_results: int = 5) -> Dict[str, Any]:
    """Fetch unread emails from the executive's Outlook Inbox."""
    from agents.email_agent import EmailAgent
    agent = EmailAgent(access_token=_global_access_token)
    return await agent.execute({"action": "fetch_unread_emails", "max_results": max_results})

async def draft_email_reply(thread_id: str, draft_content: str) -> Dict[str, Any]:
    """Draft a reply to a specific email thread."""
    from agents.email_agent import EmailAgent
    agent = EmailAgent(access_token=_global_access_token)
    return await agent.execute({
        "action": "draft_email_reply",
        "thread_id": thread_id,
        "draft_content": draft_content
    })

async def query_knowledge_base(query: str) -> Dict[str, Any]:
    """Query the personal knowledge base (RAG) for information from previously uploaded documents."""
    from agents.knowledge_agent import KnowledgeAgent
    agent = KnowledgeAgent()
    return await agent.execute({"action": "query", "query": query})
