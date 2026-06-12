import json
from typing import Dict, Any
from .base_agent import BaseAgent
from utils.memory_db import MemoryDB
from utils.pdf_export import PDFExporter

class BriefingAgent(BaseAgent):
    """Agent responsible for generating executive briefings and PPT outlines."""
    
    def __init__(self):
        super().__init__(name="BriefingAgent", role="Executive Briefing Generator")
        self.memory = MemoryDB()

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
        
        # Save to persistent memory
        self.log_action("Saving briefing to persistent memory...")
        self.memory.save_briefing(subject, briefing_md)
        
        # Generate PDF
        pdf_filename = f"briefing_{subject.replace(' ', '_').lower()}.pdf"
        self.log_action(f"Exporting PDF to outputs/{pdf_filename}...")
        pdf_path = PDFExporter.export_markdown_to_pdf(briefing_md, pdf_filename)
        
        # Generate PPT Outline
        ppt_outline = await self._generate_ppt_outline(subject, briefing_md)
        
        self.log_action("Briefing generation complete!")
        
        return {
            "status": "success",
            "meeting_subject": subject,
            "briefing_markdown": briefing_md,
            "pdf_path": pdf_path,
            "ppt_outline": ppt_outline
        }

    async def _generate_briefing(self, subject: str, research: str, calendar: str) -> str:
        """Generate a structured Markdown briefing document."""
        prompt = f"""
        Create a highly detailed and comprehensive professional executive briefing document for the following meeting. Do not arbitrarily limit the length to 1 page if more space is needed for thorough details.
        
        MEETING: {subject}
        
        RESEARCH FINDINGS:
        {research}
        
        CALENDAR CONTEXT:
        {calendar}
        
        FORMAT REQUIREMENTS:
        Use Markdown. Include these exact sections:
        1. **EXECUTIVE SUMMARY** (Comprehensive overview of the topic)
        2. **KEY ATTENDEE BACKGROUND** (Detailed context on who they are and their stakes)
        3. **DETAILED DEVELOPMENTS & FINDINGS** (Exhaustive details, statistics, and facts from the research)
        4. **IN-DEPTH DISCUSSION POINTS** (Extensive strategic points and deep analysis)
        5. **CRITICAL QUESTIONS** (All relevant strategic questions to consider)
        6. **ACTION ITEMS** (Concrete and extensive next steps)
        
        STRICT INSTRUCTIONS:
        - Do NOT hallucinate, guess, or make assumptions.
        - Only use the exact facts provided in the RESEARCH FINDINGS and CALENDAR CONTEXT.
        - Be highly detailed but strictly relevant to the point.
        - Be highly detailed, comprehensive, and strictly relevant. Do not leave out important context.
        """
        
        messages = self._build_messages(
            system_prompt="You are an elite executive assistant. Create crisp, high-impact briefing documents. Strictly enforce factual reporting. Do not hallucinate, guess, or make assumptions. Only use the provided research and calendar data. Be highly detailed but strictly relevant to the point.",
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