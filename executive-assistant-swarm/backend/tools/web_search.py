import aiohttp
import logging
from typing import List, Dict
from utils.config import settings

logger = logging.getLogger(__name__)

class BingSearchTool:
    """Tool for performing Bing web searches"""
    
    def __init__(self):
        self.api_key = settings.BING_SEARCH_API_KEY
        self.endpoint = settings.BING_SEARCH_ENDPOINT
        self.headers = {"Ocp-Apim-Subscription-Key": self.api_key}
    
    async def search(self, query: str, count: int = 5) -> List[Dict]:
        """
        Search the web using Bing API
        
        Args:
            query: Search query string
            count: Number of results to return (max 50)
        
        Returns:
            List of search results
        """
        if not self.api_key:
            logger.warning("Bing API key not configured, returning mock results")
            return self._get_mock_results(query, count)
        
        params = {
            "q": query,
            "count": min(count, 50),  # Bing API max is 50
            "mkt": "en-US",
            "safeSearch": "Moderate"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.endpoint,
                    headers=self.headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("webPages", {}).get("value", [])
                        logger.info(f"Bing search returned {len(results)} results for: {query}")
                        return results
                    else:
                        logger.error(f"Bing API error: {response.status}, returning mock results")
                        return self._get_mock_results(query, count)
        except Exception as e:
            logger.error(f"Bing search failed: {e}")
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