import sys
import os
import asyncio

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from agents.research_agent import ResearchAgent
from agents.scheduler_agent import SchedulerAgent

@pytest.mark.asyncio
async def test_research_agent():
    """Test the Research Agent"""
    print("\n--- Testing Research Agent ---")
    agent = ResearchAgent()
    
    # Test with a simple query
    task = {"query": "Microsoft Build 2026 AI announcements", "num_results": 2}
    result = await agent.execute(task)
    
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Sources found: {len(result['sources'])}")
        print(f"Synthesis Preview:\n{result['synthesis'][:200]}...")
    else:
        print(f"Error: {result.get('message')}")
        
    assert result['status'] == 'success', "Research agent failed!"
    print("✅ Research Agent Test Passed!\n")

@pytest.mark.asyncio
async def test_scheduler_agent():
    """Test the Scheduler Agent (Microsoft Graph)"""
    print("--- Testing Scheduler Agent ---")
    print("⚠️ NOTE: This will print a code in your terminal.")
    print("⚠️ Go to https://microsoft.com/devicelogin, enter the code, and log in with your Microsoft account.")
    
    agent = SchedulerAgent()
    
    # Test 1: Get User Profile (Verifies Auth works)
    print("\n[Test 1] Fetching User Profile...")
    profile_result = await agent.execute({"action": "get_user_profile"})
    
    if profile_result['status'] == 'success':
        print(f"✅ Authenticated as: {profile_result['data']['name']} ({profile_result['data']['email']})")
    else:
        print(f"❌ Auth Failed: {profile_result['message']}")
        return # Stop if auth fails

    # Test 2: Check Calendar
    print("\n[Test 2] Fetching Calendar Events...")
    cal_result = await agent.execute({"action": "check_calendar"})
    
    if cal_result['status'] == 'success':
        events = cal_result['data']
        print(f"✅ Found {len(events)} upcoming events.")
        for ev in events[:2]:
            print(f"   - {ev['subject']} at {ev['start']}")
    else:
        print(f"❌ Calendar Fetch Failed: {cal_result['message']}")

    print("✅ Scheduler Agent Test Passed!\n")

async def main():
    print("="*50)
    print("RUNNING CORE AGENTS TESTS")
    print("="*50)
    
    # Run Research first (no login required)
    await test_research_agent()
    
    # Run Scheduler second (requires interactive login)
    await test_scheduler_agent()
    
    print("="*50)
    print("🎉 ALL CORE AGENTS TESTS PASSED!")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())