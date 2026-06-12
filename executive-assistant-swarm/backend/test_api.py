import asyncio
import json
import base64
import aiohttp

async def main():
    with open("dummy.pdf", "rb") as f:
        file_bytes = f.read()
    file_b64 = base64.b64encode(file_bytes).decode('utf-8')
    
    payload = {
        "user_prompt": "Please analyze this document.",
        "file_name": "dummy.pdf",
        "file_base64": file_b64,
        "chat_history": []
    }
    
    async with aiohttp.ClientSession() as session:
        print("Sending request to API...")
        async with session.post("http://localhost:8000/execute/stream", json=payload) as response:
            print("Status:", response.status)
            async for line in response.content:
                if line:
                    print(line.decode('utf-8').strip())

if __name__ == "__main__":
    asyncio.run(main())
