import json
from typing import Dict, Any
from .base_agent import BaseAgent

class BriefingAgent(BaseAgent):
    """Agent responsible for generating executive briefings and PPT outlines."""
    
    def __init__(self):
        super().__init__(name="BriefingAgent", role="Executive Briefing Generator")

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task format:
        {
            "meeting_subject": "Meeting with Acme Corp",
            "research_synthesis": "...",
            "calendar_context": "..."
        }
        """
        subject = task.get("meeting_subject", "Executive Meeting")
        research = task.get("research_synthesis", "No research provided.")
        calendar = task.get("calendar_context", "No calendar context provided.")
        
        self.log_action(f"Generating briefing for: '{subject}'")
        
        # Generate Markdown Briefing
        briefing_md = await self._generate_briefing(subject, research, calendar)
        
        # Generate PPT Outline
        ppt_outline = await self._generate_ppt_outline(subject, briefing_md)
        
        self.log_action("Briefing generation complete!")
        
        return {
            "status": "success",
            "meeting_subject": subject,
            "briefing_markdown": briefing_md,
            "ppt_outline": ppt_outline
        }

    async def _generate_briefing(self, subject: str, research: str, calendar: str) -> str:
        """Generate a structured Markdown briefing document."""
        prompt = f"""
        Create a professional, 1-page executive briefing document for the following meeting.
        
        MEETING: {subject}
        
        RESEARCH FINDINGS:
        {research}
        
        CALENDAR CONTEXT:
        {calendar}
        
        FORMAT REQUIREMENTS:
        Use Markdown. Include these exact sections:
        1. **EXECUTIVE SUMMARY** (2-3 sentences max)
        2. **KEY ATTENDEE BACKGROUND** (Brief context on who they are)
        3. **RECENT DEVELOPMENTS** (3 bullet points from research)
        4. **KEY DISCUSSION POINTS** (3-5 strategic bullet points)
        5. **POTENTIAL QUESTIONS** (2-3 questions they might ask)
        6. **ACTION ITEMS** (3 next steps)
        
        Be concise, professional, and action-oriented. No fluff.
        """
        
        messages = self._build_messages(
            system_prompt="You are an elite executive assistant. Create crisp, high-impact briefing documents.",
            user_message=prompt
        )
        
        return self._call_llm(messages, temperature=0.4)

    async def _generate_ppt_outline(self, subject: str, briefing_md: str) -> str:
        """Generate a 5-slide PowerPoint outline based on the briefing."""
        prompt = f"""
        Based on this briefing for '{subject}', create a 5-slide PowerPoint presentation outline.
        
        BRIEFING:
        {briefing_md[:1000]}...
        
        FORMAT:
        Slide 1: Title Slide (Title, Subtitle)
        Slide 2: Executive Summary
        Slide 3: Key Findings & Data
        Slide 4: Strategic Discussion Points
        Slide 5: Next Steps & Action Items
        
        For each slide, provide the Title and 3-4 concise bullet points.
        """
        
        messages = self._build_messages(
            system_prompt="You are a presentation expert. Create clear, impactful slide outlines.",
            user_message=prompt
        )
        
        return self._call_llm(messages, temperature=0.4)