import aiohttp
from bs4 import BeautifulSoup
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class WebScraperTool:
    """Tool for extracting content from web pages"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def extract_content(self, url: str, max_length: int = 3000) -> str:
        """
        Extract text content from a web page
        
        Args:
            url: URL to scrape
            max_length: Maximum length of extracted text
        
        Returns:
            Extracted text content
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        html = await response.text()
                        return self._parse_html(html, max_length)
                    else:
                        logger.error(f"Failed to fetch {url}: {response.status}")
                        return f"Error: Could not fetch {url}"
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return f"Error scraping {url}: {str(e)}"
    
    def _parse_html(self, html: str, max_length: int) -> str:
        """Parse HTML and extract text content"""
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header", "iframe"]):
                element.decompose()
            
            # Get text content
            text = soup.get_text(separator=' ', strip=True)
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit length
            return text[:max_length]
        except Exception as e:
            logger.error(f"Error parsing HTML: {e}")
            return f"Error parsing HTML: {str(e)}"