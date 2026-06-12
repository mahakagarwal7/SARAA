from abc import ABC, abstractmethod
from typing import Dict, List, Any
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.conversation_history: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        
        # Initialize Azure OpenAI client
        try:
            from utils.config import settings
            # Azure AI Inference SDK expects the full deployment URL when targeting Azure OpenAI
            full_endpoint = f"{settings.AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/deployments/{settings.AZURE_OPENAI_DEPLOYMENT_NAME}"
            self.client = ChatCompletionsClient(
                endpoint=full_endpoint,
                credential=AzureKeyCredential(settings.AZURE_OPENAI_API_KEY),
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME
            )
            logger.info(f"{self.name} initialized with Azure OpenAI")
        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            self.client = None
    
    def _build_messages(self, system_prompt: str, user_message: str) -> List:
        """Build messages for LLM"""
        messages = [
            SystemMessage(content=system_prompt),
            UserMessage(content=user_message)
        ]
        return messages
    
    def _call_llm(self, messages: List, temperature: float = 0.7) -> str:
        """Call Azure OpenAI LLM"""
        if not self.client:
            raise Exception("LLM client not initialized")
        
        try:
            response = self.client.complete(
                messages=messages,
                temperature=temperature,
                max_tokens=4096
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def log_action(self, action: str, level: str = "INFO"):
        """Log agent action"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{self.name}] {action}"
        
        if level == "INFO":
            logger.info(log_message)
        elif level == "ERROR":
            logger.error(log_message)
        elif level == "DEBUG":
            logger.debug(log_message)
    
    def add_to_history(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics"""
        return {
            "name": self.name,
            "role": self.role,
            "messages_in_history": len(self.conversation_history),
            "created_at": self.created_at.isoformat()
        }
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute agent task - to be implemented by subclasses"""
        pass