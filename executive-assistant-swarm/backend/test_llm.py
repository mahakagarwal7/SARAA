import asyncio
import os
from dotenv import load_dotenv
load_dotenv(override=True)
from agents.orchestrator_agent import OrchestratorAgent

async def main():
    agent = OrchestratorAgent()
    try:
        # Create a large dummy text
        text = "Hello " * 10000
        print("Calling compile_summary with large text...")
        res = await agent._compile_summary(f"User Request: Analyze this file. [ATTACHED DOCUMENT 'test.txt' CONTENTS:\n{text}]", {"test": "test"})
        print("RESULT:")
        print(res)
    except Exception as e:
        print("ERROR:", e)

if __name__ == "__main__":
    asyncio.run(main())
