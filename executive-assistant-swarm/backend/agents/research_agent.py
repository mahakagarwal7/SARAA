import json
import asyncio
from typing import Dict, Any, List
from .base_agent import BaseAgent
from tools.web_search import BingSearchTool
from tools.web_scraper import WebScraperTool

class ResearchAgent(BaseAgent):
    """Agent responsible for browsing the web and extracting information."""
    
    def __init__(self):
        super().__init__(name="ResearchAgent", role="Web Research Specialist")
        self.search_tool = BingSearchTool()
        self.scraper_tool = WebScraperTool()

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task format: 
        {
            "query": "What to research",
            "num_results": 3
        }
        """
        query = task.get("query", "latest AI news")
        num_results = task.get("num_results", 3)
        
        self.log_action(f"Starting research on: '{query}'")
        
        # 1. Search the web
        self.log_action("Searching Bing...")
        search_results = await self.search_tool.search(query, count=num_results)
        
        if not search_results:
            self.log_action("No search results found.", level="WARNING")
            return {"status": "error", "message": "No search results found."}

        # 2. Scrape the top 2 results for deeper context
        self.log_action(f"Scraping top {min(2, len(search_results))} URLs for details...")
        scraped_content = []
        for result in search_results[:2]:
            url = result.get("url")
            if url:
                content = await self.scraper_tool.extract_content(url, max_length=1500)
                scraped_content.append({
                    "title": result.get("name"),
                    "url": url,
                    "content": content
                })

        # 3. Synthesize the findings using the LLM
        self.log_action("Synthesizing research with LLM...")
        synthesis = await self._synthesize_findings(query, search_results, scraped_content)
        
        self.log_action("Research complete!")
        
        return {
            "status": "success",
            "query": query,
            "sources": [{"title": r.get("name"), "url": r.get("url")} for r in search_results],
            "synthesis": synthesis
        }

    async def _synthesize_findings(self, query: str, search_results: List, scraped_content: List) -> str:
        """Use LLM to summarize the raw web data."""
        
        # Format data for the prompt
        snippets = "\n".join([f"- {r.get('name')}: {r.get('snippet')}" for r in search_results])
        details = "\n\n".join([f"Source: {c.get('title')}\n{c.get('content')[:500]}..." for c in scraped_content])

        prompt = f"""
        You are an expert research assistant. 
        Query: "{query}"
        
        Search Snippets:
        {snippets}
        
        Detailed Content:
        {details}
        
        Task: Provide a concise, 3-4 bullet point executive summary of the findings. Focus on facts, numbers, and key takeaways. Do not include fluff.
        """
        
        messages = self._build_messages(
            system_prompt="You are an expert research analyst. Provide clear, factual, and concise summaries.",
            user_message=prompt
        )
        
        # Note: _call_llm is synchronous in our base class, which is fine for this step.
        return self._call_llm(messages, temperature=0.3)