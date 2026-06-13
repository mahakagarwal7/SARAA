import sys
import os
import asyncio

# Ensure backend is in path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

async def test_agents():
    print("Testing imports and initialization...")
    try:
        from agents.email_agent import EmailAgent
        from agents.knowledge_agent import KnowledgeAgent
        from agents.orchestrator_agent import OrchestratorAgent
        
        email_agent = EmailAgent(access_token="mock_token")
        knowledge_agent = KnowledgeAgent()
        orchestrator = OrchestratorAgent(use_mock_scheduler=True)
        
        print("Initialization successful!")
        
        print("Testing Knowledge Base Query (mock)...")
        res = await knowledge_agent.execute({"action": "query", "query": "test"})
        print("Knowledge Agent Result:", res)
        
        print("Testing Email Agent (mock)...")
        res2 = await email_agent.execute({"action": "fetch_unread_emails"})
        print("Email Agent Result:", res2)
        
        print("All local tests passed!")
        
    except Exception as e:
        print(f"Error during initialization/testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agents())
