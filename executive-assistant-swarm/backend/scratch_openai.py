import autogen
from openai import AzureOpenAI

client = AzureOpenAI(
    azure_endpoint="https://saraa-resource.services.ai.azure.com/",
    api_key="dummy",
    api_version="2024-05-01-preview"
)

print("OpenAI client deployment path:", client._custom_query)
