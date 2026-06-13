import autogen
import asyncio

llm_config = {
    "config_list": [{
        "model": "gpt-4.1-mini",
        "api_key": "dummy",
        "base_url": "https://saraa-resource.services.ai.azure.com/openai/deployments/gpt-4.1-mini",
        "api_type": "openai",
        "default_query": {"api-version": "2024-05-01-preview"}
    }]
}
agent = autogen.AssistantAgent(name="test", llm_config=llm_config)
print("AGENT CLIENT CONFIG:", agent.client._config_list)
