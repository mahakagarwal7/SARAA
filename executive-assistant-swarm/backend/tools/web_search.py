import aiohttp
import logging
from typing import List, Dict
from utils.config import settings

logger = logging.getLogger(__name__)

class TavilySearchTool:
    """Tool for performing web searches using Tavily API"""
    
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.endpoint = settings.TAVILY_ENDPOINT
    
    async def search(self, query: str, count: int = 5) -> List[Dict]:
        """
        Search the web using Tavily API
        
        Args:
            query: Search query string
            count: Number of results to return
        
        Returns:
            List of search results
        """
        if not self.api_key:
            logger.warning("Tavily API key not configured, returning mock results")
            return self._get_mock_results(query, count)
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": min(count, 10),  # Limit to 10 for basic requests
            "include_answer": False
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        raw_results = data.get("results", [])
                        
                        # Map Tavily fields to the format expected by the ResearchAgent
                        results = []
                        for r in raw_results:
                            results.append({
                                "name": r.get("title", ""),
                                "url": r.get("url", ""),
                                "snippet": r.get("content", "")
                            })
                            
                        logger.info(f"Tavily search returned {len(results)} results for: {query}")
                        return results
                    else:
                        error_text = await response.text()
                        logger.error(f"Tavily API error: {response.status} - {error_text}, returning mock results")
                        return self._get_mock_results(query, count)
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return self._get_mock_results(query, count)
    
    def _get_mock_results(self, query: str, count: int) -> List[Dict]:
        """Return mock results for testing"""
        logger.info("Returning mock search results")
        return [
            {
                "name": f"Result {i+1} for {query}",
                "url": f"https://example.com/result-{i+1}",
                "snippet": f"This is a mock snippet for result {i+1} about {query}"
            }
            for i in range(count)
        ]