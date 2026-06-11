from typing import Dict, Any
from .base_agent import BaseAgent

class WriterAgent(BaseAgent):
    """Agent responsible for drafting follow-up emails, memos, and announcements."""
    
    def __init__(self):
        super().__init__(name="WriterAgent", role="Professional Document Drafter")

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task format:
        {
            "briefing_markdown": "...",
            "user_request": "Draft an email to my team about the meeting",
            "document_type": "email" # optional, or could be "memo", "announcement"
        }
        """
        briefing = task.get("briefing_markdown", "No briefing provided.")
        user_request = task.get("user_request", "Draft a professional document based on the briefing.")
        document_type = task.get("document_type", "document")
        
        self.log_action(f"Drafting {document_type} based on user request...")
        
        draft = await self._draft_document(briefing, user_request, document_type)
        
        self.log_action(f"Draft generation complete!")
        
        return {
            "status": "success",
            "draft_document": draft,
            "document_type": document_type
        }

    async def _draft_document(self, briefing: str, user_request: str, document_type: str) -> str:
        """Generate a draft document based on the briefing."""
        prompt = f"""
        Draft a professional {document_type} based on the following executive briefing and user request.
        
        USER REQUEST:
        {user_request}
        
        EXECUTIVE BRIEFING:
        {briefing}
        
        INSTRUCTIONS:
        - Ensure the tone is appropriate for a professional {document_type}.
        - Do not hallucinate any information; strictly use the facts from the briefing.
        - Make it well-structured, clear, and ready to send/publish.
        """
        
        messages = self._build_messages(
            system_prompt="You are an expert professional document drafter. You create clear, impactful, and fact-based emails, memos, and announcements.",
            user_message=prompt
        )
        
        return self._call_llm(messages, temperature=0.4)
