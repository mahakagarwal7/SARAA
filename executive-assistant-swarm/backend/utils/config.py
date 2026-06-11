import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

class Settings:
    """Application settings"""
    
    # Azure OpenAI
    AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
    AZURE_OPENAI_API_VERSION: str = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    # Microsoft Graph
    CLIENT_ID: str = os.getenv("CLIENT_ID", "")
    CLIENT_SECRET: str = os.getenv("CLIENT_SECRET", "")
    TENANT_ID: str = os.getenv("TENANT_ID", "")
    REDIRECT_URI: str = os.getenv("REDIRECT_URI", "http://localhost:8000/auth/callback")
    
    # Tavily Search
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    TAVILY_ENDPOINT: str = os.getenv("TAVILY_ENDPOINT", "https://api.tavily.com/search")
    
    # Telemetry
    APPLICATIONINSIGHTS_CONNECTION_STRING: str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "")
    
    # Application
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    def validate(self) -> bool:
        """Validate required settings"""
        required = [
            self.AZURE_OPENAI_ENDPOINT,
            self.AZURE_OPENAI_API_KEY,
            self.CLIENT_ID,
            self.CLIENT_SECRET,
            self.TENANT_ID,
        ]
        return all(required)

# Global settings instance
settings = Settings()