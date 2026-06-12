import asyncio
from agents.orchestrator_agent import OrchestratorAgent

async def main():
    agent = OrchestratorAgent()
    try:
        async for msg in agent.execute_stream("Check out Fifa World cup details"):
            print(msg)
    except Exception as e:
        print("EXCEPTION:", type(e), e)

asyncio.run(main())
