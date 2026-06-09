import sys
import os
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.orchestrator_agent import OrchestratorAgent

async def test_full_swarm():
    print("\n" + "="*60)
    print("🚀 TESTING FULL AGENT SWARM (End-to-End)")
    print("="*60)
    
    # Initialize with MOCK scheduler so we can test without Graph API login!
    # When your teammate fixes the Graph API, change this to: OrchestratorAgent(use_mock_scheduler=False)
    swarm = OrchestratorAgent(use_mock_scheduler=True)
    
    # The Golden Path Demo Scenario
    user_prompt = "I have a strategy meeting with Contoso next week. Research their latest AI product launches, check my calendar for conflicts, and generate a prep briefing."
    
    print(f"\n USER PROMPT: '{user_prompt}'\n")
    print(" Swarm is processing... (This will take 15-30 seconds)\n")
    
    result = await swarm.execute(user_prompt)
    
    print("\n" + "-"*60)
    print("📊 EXECUTION LOG:")
    print("-"*60)
    for log in result['execution_log']:
        status_emoji = "✅" if log['status'] == 'success' else "❌"
        print(f"{status_emoji} {log['agent']}: {log['status']}")
        
    print("\n" + "-"*60)
    print("📝 FINAL SUMMARY:")
    print("-"*60)
    print(result['final_summary'])
    
    print("\n" + "="*60)
    print("🎉 FULL SWARM TEST PASSED!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_full_swarm())