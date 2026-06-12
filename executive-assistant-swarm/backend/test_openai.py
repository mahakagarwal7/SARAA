import openai
import os

client = openai.AzureOpenAI(
    api_key="dummy",
    azure_endpoint="https://saraa-resource.services.ai.azure.com/",
    api_version="2024-05-01-preview",
)

try:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": "hello"}]
    )
except Exception as e:
    print("EXCEPTION:", e)
