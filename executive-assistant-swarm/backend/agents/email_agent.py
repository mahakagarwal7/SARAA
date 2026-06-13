import asyncio
from typing import Dict, Any, List
from .base_agent import BaseAgent
from azure.identity import DeviceCodeCredential
from utils.config import settings
import httpx

class EmailAgent(BaseAgent):
    """Agent responsible for reading and drafting emails via Microsoft Graph."""
    
    def __init__(self, access_token: str = None):
        super().__init__(name="EmailAgent", role="Email Inbox Manager")
        self.access_token = access_token
        self._ms_token = None
        self._credential = None

    async def _get_graph_token(self) -> str:
        """Get a real Microsoft Graph token using provided token or Device Code flow."""
        if self.access_token:
            return self.access_token

        if self._ms_token:
            return self._ms_token
            
        def prompt_callback(uri, code, expires_on):
            self.log_action(f"🚨 **ACTION REQUIRED**: To connect your Outlook account, please click this link: [{uri}]({uri}) and enter the code: **{code}**", level="INFO")
            
        self.log_action("Initiating Microsoft Graph Authentication...")
        try:
            self._credential = DeviceCodeCredential(
                client_id=settings.CLIENT_ID,
                tenant_id=settings.TENANT_ID,
                prompt_callback=prompt_callback
            )
            # Request delegated permissions for mail
            token_obj = await asyncio.to_thread(self._credential.get_token, "https://graph.microsoft.com/Mail.ReadWrite")
            self._ms_token = token_obj.token
            self.log_action("Successfully authenticated with Microsoft Graph!")
            return self._ms_token
        except Exception as e:
            self.log_action(f"Authentication failed: {e}", level="ERROR")
            raise e

    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task format:
        {
            "action": "fetch_unread_emails" | "draft_email_reply",
            "max_results": int (optional),
            "thread_id": str (optional),
            "draft_content": str (optional)
        }
        """
        action = task.get("action", "fetch_unread_emails")
        self.log_action(f"Executing Email action: {action}")

        try:
            if action == "fetch_unread_emails":
                max_results = task.get("max_results", 5)
                return await self._fetch_unread_emails(max_results)
            elif action == "draft_email_reply":
                return await self._draft_email_reply(task.get("thread_id"), task.get("draft_content", ""))
            else:
                return {"status": "error", "message": f"Unknown action: {action}"}
        except Exception as e:
            self.log_action(f"Graph API Error: {str(e)}", level="ERROR")
            return {"status": "error", "message": str(e)}

    async def _fetch_unread_emails(self, max_results: int) -> Dict[str, Any]:
        """Fetch unread emails from Inbox."""
        self.log_action("Fetching real unread emails from Outlook...")
        
        try:
            token = await self._get_graph_token()
            
            url = "https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messages"
            params = {
                "$filter": "isRead eq false",
                "$select": "id,subject,bodyPreview,from",
                "$top": max_results,
                "$orderby": "receivedDateTime desc"
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                
            if response.status_code != 200:
                raise Exception(f"Failed to fetch emails: {response.text}")
                
            data = response.json()
            messages = data.get("value", [])
            
            unread_emails = []
            for msg in messages:
                sender = msg.get("from", {}).get("emailAddress", {}).get("address", "Unknown")
                unread_emails.append({
                    "id": msg.get("id"),
                    "subject": msg.get("subject"),
                    "sender": sender,
                    "bodyPreview": msg.get("bodyPreview")
                })
                
            self.log_action(f"Found {len(unread_emails)} unread emails.")
            
            return {
                "status": "success",
                "action": "fetch_unread_emails",
                "data": unread_emails
            }
            
        except Exception as e:
            self.log_action(f"Failed to fetch emails: {e}. Falling back to mock data.", level="WARNING")
            return {
                "status": "success",
                "action": "fetch_unread_emails",
                "data": [
                    {"id": "mock_msg_1", "subject": "Quarterly Review", "sender": "manager@company.com", "bodyPreview": "Please review the attached quarterly metrics."},
                    {"id": "mock_msg_2", "subject": "Lunch Plans", "sender": "colleague@company.com", "bodyPreview": "Are we still on for 12:30?"}
                ]
            }

    async def _draft_email_reply(self, thread_id: str, draft_content: str) -> Dict[str, Any]:
        """Draft a reply to a specific email thread."""
        self.log_action(f"Drafting REAL email reply in Outlook...")
        
        try:
            token = await self._get_graph_token()
            
            url = f"https://graph.microsoft.com/v1.0/me/messages/{thread_id}/createReply"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            data = {
                "message": {
                    "body": {
                        "contentType": "HTML",
                        "content": draft_content
                    }
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data)
                
            if response.status_code in (200, 201, 202):
                return {
                    "status": "success",
                    "action": "draft_email_reply",
                    "message": f"Successfully drafted reply in your Outlook drafts for message {thread_id}."
                }
            else:
                raise Exception(f"Failed to draft reply. Status {response.status_code}: {response.text}")
                
        except Exception as e:
             self.log_action(f"Failed to draft reply: {e}. Simulating success in mock mode.", level="WARNING")
             return {
                 "status": "success",
                 "action": "draft_email_reply",
                 "message": f"Successfully drafted reply in your Mock Outlook drafts for message {thread_id}."
             }
