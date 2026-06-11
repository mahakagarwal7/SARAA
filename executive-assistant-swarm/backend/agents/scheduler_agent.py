import asyncio
from typing import Dict, Any
from .base_agent import BaseAgent
from azure.identity import DeviceCodeCredential
from azure.core.credentials import AccessToken
from msgraph import GraphServiceClient

from utils.config import settings

class StaticTokenCredential:
    def __init__(self, token: str):
        self.token = token
    def get_token(self, *scopes, **kwargs) -> AccessToken:
        import time
        return AccessToken(self.token, int(time.time()) + 3600)

class SchedulerAgent(BaseAgent):
    """Agent responsible for Calendar and Email via Microsoft Graph."""
    
    def __init__(self, access_token: str = None):
        super().__init__(name="SchedulerAgent", role="Calendar & Email Coordinator")
        self.access_token = access_token
        self.graph_client = self._init_graph_client()

    def _init_graph_client(self):
        """Initialize Microsoft Graph Client using provided access token or fallback to Device Code Flow."""
        self.log_action("Initializing Microsoft Graph Client...")
        
        if not self.access_token and ("your-" in settings.TENANT_ID or "your-" in settings.CLIENT_ID):
            self.log_action("Dummy MS Graph credentials detected and no token provided. Operating in mock mode.", level="WARNING")
            self.mock_mode = True
            return None

        self.mock_mode = False
        
        if self.access_token:
            self.log_action("Using provided Entra ID Access Token from frontend.")
            credential = StaticTokenCredential(self.access_token)
        else:
            self.log_action("Using Device Code Flow for local backend testing.")
            credential = DeviceCodeCredential(
                client_id=settings.CLIENT_ID,
                tenant_id=settings.TENANT_ID
            )
        
        # Scopes needed for Calendar and Mail
        scopes = ['Calendars.Read', 'Calendars.ReadWrite', 'Mail.Send', 'User.Read']
        
        return GraphServiceClient(credentials=credential, scopes=scopes)

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task format:
        {
            "action": "check_calendar" | "get_user_profile",
            "date": "YYYY-MM-DD" (optional)
        }
        """
        action = task.get("action", "get_user_profile")
        self.log_action(f"Executing Graph action: {action}")

        try:
            if action == "get_user_profile":
                return await self._get_user_profile()
            elif action == "check_calendar":
                return await self._check_calendar()
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            self.log_action(f"Graph API Error: {str(e)}", level="ERROR")
            return {"status": "error", "message": str(e)}

    async def _get_user_profile(self) -> Dict[str, Any]:
        """Fetch the current user's profile to verify connection."""
        self.log_action("Fetching user profile from Graph API...")
        
        if getattr(self, "mock_mode", False):
            return {
                "status": "success",
                "action": "get_user_profile",
                "data": {
                    "name": "Mock User (Dummy Auth)",
                    "email": "mock@example.com",
                    "job_title": "Executive (Mock)"
                }
            }
            
        user = await self.graph_client.me.get()
        
        self.log_action(f"Successfully connected as: {user.display_name}")
        return {
            "status": "success",
            "action": "get_user_profile",
            "data": {
                "name": user.display_name,
                "email": user.mail or user.user_principal_name,
                "job_title": user.job_title
            }
        }

    async def _check_calendar(self) -> Dict[str, Any]:
        """Fetch upcoming calendar events."""
        self.log_action("Fetching upcoming calendar events...")
        
        if getattr(self, "mock_mode", False):
            return {
                "status": "success",
                "action": "check_calendar",
                "data": [
                    {"subject": "Mock Hackathon Sync", "start": "2026-06-10T10:00:00Z", "end": "2026-06-10T11:00:00Z"},
                    {"subject": "Mock Project Review", "start": "2026-06-11T14:00:00Z", "end": "2026-06-11T15:00:00Z"}
                ]
            }
        
        # Get the next 5 events

        
        # Note: Depending on the exact msgraph-sdk version, the syntax might slightly vary.
        # This is the standard v1.0.0 approach.
        events = await self.graph_client.me.events.get()
        
        upcoming_events = []
        if events and events.value:
            for event in events.value[:5]:
                upcoming_events.append({
                    "subject": event.subject,
                    "start": event.start.date_time if event.start else "N/A",
                    "end": event.end.date_time if event.end else "N/A"
                })
                
        self.log_action(f"Found {len(upcoming_events)} upcoming events.")
        
        return {
            "status": "success",
            "action": "check_calendar",
            "data": upcoming_events
        }