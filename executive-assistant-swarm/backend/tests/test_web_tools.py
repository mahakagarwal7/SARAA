import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import pytest
from tools.web_search import BingSearchTool
from tools.web_scraper import WebScraperTool

@pytest.mark.asyncio
async def test_bing_search():
    """Test Bing search functionality"""
    print("\n=== Testing Bing Search ===")
    
    tool = BingSearchTool()
    
    # Test search
    results = await tool.search("Microsoft AI announcements 2024", count=3)
    
    print(f"✓ Search returned {len(results)} results")
    
    if results:
        print(f"  First result: {results[0]['name']}")
        print(f"  URL: {results[0]['url']}")
    
    assert len(results) > 0, "Search should return at least one result"
    print("✓ Bing search test passed")

@pytest.mark.asyncio
async def test_web_scraper():
    """Test web scraper functionality"""
    print("\n=== Testing Web Scraper ===")
    
    tool = WebScraperTool()
    
    # Test scraping a simple page
    url = "https://example.com"
    content = await tool.extract_content(url, max_length=500)
    
    print(f"✓ Scraped {len(content)} characters from {url}")
    print(f"  Preview: {content[:100]}...")
    
    assert len(content) > 0, "Scraper should return content"
    print("✓ Web scraper test passed")

@pytest.mark.asyncio
async def test_combined_workflow():
    """Test search + scrape workflow"""
    print("\n=== Testing Combined Workflow ===")
    
    search_tool = BingSearchTool()
    scrape_tool = WebScraperTool()
    
    # Search
    results = await search_tool.search("Python programming", count=2)
    print(f"✓ Found {len(results)} results")
    
    # Scrape first result
    if results:
        url = results[0]['url']
        content = await scrape_tool.extract_content(url, max_length=300)
        print(f"✓ Scraped content from first result ({len(content)} chars)")
    
    print("✓ Combined workflow test passed")

async def run_all_tests():
    """Run all web tools tests"""
    print("\n" + "="*50)
    print("RUNNING WEB TOOLS TESTS")
    print("="*50)
    
    await test_bing_search()
    await test_web_scraper()
    await test_combined_workflow()
    
    print("\n" + "="*50)
    print("✅ ALL WEB TOOLS TESTS PASSED!")
    print("="*50 + "\n")

if __name__ == "__main__":
    asyncio.run(run_all_tests())