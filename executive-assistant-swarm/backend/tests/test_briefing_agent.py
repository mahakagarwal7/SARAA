import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from agents.briefing_agent import BriefingAgent

@pytest.mark.asyncio
async def test_briefing_agent():
    print("\n--- Testing Briefing Agent ---")
    agent = BriefingAgent()
    
    # Mock data to simulate inputs from other agents
    task = {
        "meeting_subject": "Q3 Strategy Review with Contoso",
        "research_synthesis": "Contoso recently launched a new AI platform. Their Q2 revenue grew 15%. They are looking to expand into the European market.",
        "calendar_context": "Meeting is scheduled for next Tuesday at 2 PM. 45 minutes. Attendees: CEO and CTO of Contoso."
    }
    
    result = await agent.execute(task)
    
    if result['status'] == 'success':
        print("✅ Briefing generated successfully!")
        print("\n--- BRIEFING PREVIEW ---")
        print(result['briefing_markdown'][:500] + "...")
        print("\n--- PPT OUTLINE PREVIEW ---")
        print(result['ppt_outline'][:300] + "...")
    else:
        print(f"❌ Failed: {result}")

    assert result['status'] == 'success', "Briefing agent failed!"
    print("\n✅ Briefing Agent Test Passed!\n")

if __name__ == "__main__":
    asyncio.run(test_briefing_agent())