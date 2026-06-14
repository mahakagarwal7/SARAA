import sys
import os
import asyncio
import json
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import jwt
import uuid
import bcrypt

SECRET_KEY = "super_secret_key" # Replace in production
ALGORITHM = "HS256"

# Telemetry
try:
    from azure.monitor.opentelemetry import configure_azure_monitor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    TELEMETRY_AVAILABLE = True
except ImportError as e:
    print(f"Telemetry packages not available: {e}")
    TELEMETRY_AVAILABLE = False

# CRITICAL: Add the backend root directory to sys.path so imports work correctly
# when running from the 'api' subfolder.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.orchestrator_agent import OrchestratorAgent
from utils.config import settings
from utils.memory_db import MemoryDB

memory_db = MemoryDB()

def get_user_id_from_token(token: Optional[str]) -> str:
    if not token:
        return "user_123"  # Fallback
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded.get("sub") or "user_123"
    except Exception:
        return "user_123"

# Initialize FastAPI App
app = FastAPI(
    title="Executive Assistant Agent Swarm API",
    description="REST API for the multi-agent executive assistant",
    version="1.0.0"
)

# CORS Middleware (Crucial for React Frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Telemetry
if TELEMETRY_AVAILABLE and settings.APPLICATIONINSIGHTS_CONNECTION_STRING and "your-" not in settings.APPLICATIONINSIGHTS_CONNECTION_STRING:
    try:
        configure_azure_monitor(
            connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING
        )
        FastAPIInstrumentor.instrument_app(app)
        print("Azure Application Insights telemetry enabled.")
    except Exception as e:
        print(f"Failed to initialize Azure Telemetry: {e}")
else:
    print("APPLICATIONINSIGHTS_CONNECTION_STRING not found or is mock. Running without telemetry.")

# --- Pydantic Models for Request/Response Validation ---

class SwarmRequest(BaseModel):
    user_prompt: str
    image_base64: Optional[str] = None
    file_name: Optional[str] = None
    file_base64: Optional[str] = None
    use_mock_scheduler: bool = False  # Use real scheduler by default
    chat_history: List[Dict[str, Any]] = []
    thread_id: Optional[str] = None

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str

class ForgotPasswordRequest(BaseModel):
    username: str
    email: str

class ResetPasswordRequest(BaseModel):
    username: str
    code: str
    new_password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class ThreadCreateRequest(BaseModel):
    title: str

class ExecutionLogItem(BaseModel):
    agent: str
    status: str

class SwarmResponse(BaseModel):
    status: str
    final_summary: str
    execution_log: List[ExecutionLogItem]
    results: Dict[str, Any]

class PreferenceRequest(BaseModel):
    key: str
    value: str

# --- API Endpoints ---

@app.get("/")
async def root():
    """Root endpoint to verify API is running."""
    return {
        "message": "Welcome to the Executive Assistant Agent Swarm API!",
        "docs": "/docs",
        "status": "online"
    }

@app.get("/health")
async def health_check():
    """Simple health check for monitoring."""
    return {"status": "healthy"}

@app.post("/auth/register")
async def register(req: RegisterRequest):
    if memory_db.get_user_by_username(req.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    user_id = str(uuid.uuid4())
    password_hash = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    memory_db.create_user(user_id, req.username, password_hash, req.email)
    
    token = jwt.encode({"sub": user_id, "username": req.username}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user_id, "username": req.username, "email": req.email}}

@app.post("/auth/login")
async def login(req: LoginRequest):
    user = memory_db.get_user_by_username(req.username)
    if not user or not bcrypt.checkpw(req.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    token = jwt.encode({"sub": user["id"], "username": user["username"]}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user["id"], "username": user["username"]}}

@app.post("/auth/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    user = memory_db.get_user_by_username(req.username)
    if not user or user.get("email") != req.email:
        raise HTTPException(status_code=404, detail="Username or email incorrect")
    
    # Generate random 6-digit code
    import random
    code = f"{random.randint(100000, 999999)}"
    
    memory_db.save_password_reset(req.username, req.email, code)
    
    # Check for SMTP Configuration
    smtp_host = settings.SMTP_HOST
    smtp_port = settings.SMTP_PORT
    smtp_username = settings.SMTP_USERNAME
    smtp_password = settings.SMTP_PASSWORD
    
    email_sent_via_smtp = False
    smtp_error = None
    
    if smtp_host and smtp_port and smtp_username and smtp_password:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_username
            msg['To'] = req.email
            msg['Subject'] = "SARAA Account Password Reset Code"
            
            body = (
                f"Hello {req.username},\n\n"
                f"You requested a password reset code for your SARAA account.\n\n"
                f"Your 6-digit verification code is: {code}\n\n"
                f"This code will expire in 15 minutes.\n\n"
                f"If you did not make this request, please ignore this email."
            )
            msg.attach(MIMEText(body, 'plain'))
            
            port = int(smtp_port)
            if port == 465:
                server = smtplib.SMTP_SSL(smtp_host, port, timeout=10)
            else:
                server = smtplib.SMTP(smtp_host, port, timeout=10)
                server.starttls()
                
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_username, req.email, msg.as_string())
            server.quit()
            email_sent_via_smtp = True
            print(f"SMTP: Verification code email successfully sent to {req.email}")
        except Exception as e:
            smtp_error = str(e)
            print(f"SMTP Error: Failed to send email via SMTP: {e}")
            
    # Always log the email to a local file for fallback / development purposes
    from datetime import datetime
    os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs"), exist_ok=True)
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs", "sent_emails.log")
    
    email_content = f"To: {req.email}\nSubject: Password Reset Code\n\nYour password reset code is: {code}\n"
    if not email_sent_via_smtp and smtp_error:
        email_content += f"(SMTP error: {smtp_error})\n"
        
    with open(log_path, "a") as f:
        f.write(f"[{datetime.now()}] {email_content}\n" + "="*40 + "\n")
        
    print(f"\n--- [EMAIL LOGGED] ---\n{email_content}--------------------\n")
    
    if email_sent_via_smtp:
        return {"message": "Verification code sent to your email inbox."}
    else:
        msg_detail = "Verification code generated. (Check console or sent_emails.log)"
        if smtp_error:
            msg_detail += f" SMTP Error: {smtp_error}"
        return {"message": msg_detail}

@app.post("/auth/reset-password")
async def reset_password(req: ResetPasswordRequest):
    reset_info = memory_db.get_password_reset(req.username)
    if not reset_info or reset_info["code"] != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
        
    # Check if code is expired (e.g., older than 15 minutes)
    from datetime import datetime
    try:
        created_at_val = reset_info["created_at"]
        if isinstance(created_at_val, str):
            for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                try:
                    created_at = datetime.strptime(created_at_val, fmt)
                    break
                except ValueError:
                    continue
            else:
                created_at = datetime.fromisoformat(created_at_val)
        else:
            created_at = created_at_val
    except Exception:
        created_at = datetime.now()
        
    if (datetime.now() - created_at).total_seconds() > 900:  # 15 minutes
        memory_db.delete_password_reset(req.username)
        raise HTTPException(status_code=400, detail="Verification code has expired")
        
    # Update password
    password_hash = bcrypt.hashpw(req.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    memory_db.update_user_password(req.username, password_hash)
    memory_db.delete_password_reset(req.username)
    
    return {"message": "Password reset successfully"}

@app.get("/threads")
async def get_threads(authorization: Optional[str] = Header(None)):
    token = authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None
    user_id = get_user_id_from_token(token)
    return memory_db.get_user_threads(user_id)

@app.post("/threads")
async def create_thread(req: ThreadCreateRequest, authorization: Optional[str] = Header(None)):
    token = authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None
    user_id = get_user_id_from_token(token)
    thread_id = str(uuid.uuid4())
    memory_db.create_thread(thread_id, user_id, req.title)
    return {"id": thread_id, "title": req.title}

@app.get("/threads/{thread_id}")
async def get_thread(thread_id: str, authorization: Optional[str] = Header(None)):
    token = authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None
    user_id = get_user_id_from_token(token)
    return memory_db.get_thread_messages(thread_id)

@app.post("/execute", response_model=SwarmResponse)
async def execute_swarm(
    request: SwarmRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Main endpoint: Takes a user prompt and runs the agent swarm.
    """
    if not request.user_prompt.strip():
        raise HTTPException(status_code=400, detail="user_prompt cannot be empty")

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
    user_id = get_user_id_from_token(token)

    try:
        # Initialize the orchestrator
        # Note: In a production app, you'd pool this. For a hackathon, instantiating per request is fine.
        orchestrator = OrchestratorAgent(
            use_mock_scheduler=request.use_mock_scheduler,
            access_token=token,
            user_id=user_id
        )
        
        # Execute the swarm (this is async and might take 10-30 seconds)
        result = await orchestrator.execute(
            request.user_prompt, 
            image_base64=request.image_base64, 
            file_name=request.file_name,
            file_base64=request.file_base64,
            chat_history=request.chat_history
        )
        
        return SwarmResponse(
            status=result["status"],
            final_summary=result["final_summary"],
            execution_log=[ExecutionLogItem(**log) for log in result["execution_log"]],
            results=result["results"]
        )
        
    except Exception as e:
        # Catch any errors from the agents/LLM and return a clean 500 error
        raise HTTPException(status_code=500, detail=f"Swarm execution failed: {str(e)}")

@app.post("/execute/stream")
async def execute_swarm_stream(
    request: SwarmRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Streaming endpoint: Yields Server-Sent Events (SSE) for real-time logs.
    """
    if not request.user_prompt.strip():
        raise HTTPException(status_code=400, detail="user_prompt cannot be empty")

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        
    user_id = get_user_id_from_token(token)

    async def event_generator():
        if request.thread_id:
            memory_db.add_message(request.thread_id, "user", request.user_prompt)
            
        orchestrator = OrchestratorAgent(
            use_mock_scheduler=request.use_mock_scheduler,
            access_token=token,
            user_id=user_id
        )
        try:
            async for chunk in orchestrator.execute_stream(
                request.user_prompt, 
                image_base64=request.image_base64, 
                file_name=request.file_name,
                file_base64=request.file_base64,
                chat_history=request.chat_history
            ):
                try:
                    chunk_obj = json.loads(chunk)
                    if chunk_obj.get("type") == "result" and request.thread_id:
                        memory_db.add_message(
                            request.thread_id, 
                            "assistant", 
                            chunk_obj.get("data", {}).get("final_summary", ""),
                            json.dumps(chunk_obj.get("data", {}).get("execution_log", []))
                        )
                except Exception:
                    pass
                # Yield in SSE format: data: {...}\n\n
                yield f"data: {chunk}\n\n"
        except Exception as e:
            error_msg = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/preferences")
async def get_preferences(authorization: Optional[str] = Header(None)):
    """Fetch user preferences from MemoryDB."""
    token = authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None
    user_id = get_user_id_from_token(token)
    return memory_db.get_preferences(user_id)

@app.post("/api/preferences")
async def save_preference(req: PreferenceRequest, authorization: Optional[str] = Header(None)):
    """Save a user preference to MemoryDB."""
    token = authorization.split(" ")[1] if authorization and authorization.startswith("Bearer ") else None
    user_id = get_user_id_from_token(token)
    memory_db.save_preference(user_id, req.key, req.value)
    return {"status": "success", "message": "Preference saved."}

@app.get("/api/history")
async def get_history(limit: int = 5):
    """Fetch recent briefing history from MemoryDB."""
    return memory_db.get_past_briefings(limit)

# --- Run Server Locally ---
if __name__ == "__main__":
    import uvicorn
    # Run on port 8000. Reload=True auto-restarts when you change code.
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)