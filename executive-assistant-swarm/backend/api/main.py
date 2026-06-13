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
from passlib.hash import bcrypt

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
    password_hash = bcrypt.hash(req.password)
    memory_db.create_user(user_id, req.username, password_hash)
    
    token = jwt.encode({"sub": user_id, "username": req.username}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user_id, "username": req.username}}

@app.post("/auth/login")
async def login(req: LoginRequest):
    user = memory_db.get_user_by_username(req.username)
    if not user or not bcrypt.verify(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    token = jwt.encode({"sub": user["id"], "username": user["username"]}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user["id"], "username": user["username"]}}

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