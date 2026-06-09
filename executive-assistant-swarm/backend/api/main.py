import sys
import os
import asyncio
import json
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Telemetry
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# CRITICAL: Add the backend root directory to sys.path so imports work correctly
# when running from the 'api' subfolder.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.orchestrator_agent import OrchestratorAgent
from utils.config import settings

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
if settings.APPLICATIONINSIGHTS_CONNECTION_STRING and "your-" not in settings.APPLICATIONINSIGHTS_CONNECTION_STRING:
    try:
        configure_azure_monitor(
            connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING
        )
        FastAPIInstrumentor.instrument_app(app)
        print("✅ Azure Application Insights telemetry enabled.")
    except Exception as e:
        print(f"⚠️ Failed to initialize Azure Telemetry: {e}")
else:
    print("⚠️ APPLICATIONINSIGHTS_CONNECTION_STRING not found or is mock. Running without telemetry.")

# --- Pydantic Models for Request/Response Validation ---

class SwarmRequest(BaseModel):
    user_prompt: str
    use_mock_scheduler: bool = True  # Keep True until your teammate fixes Graph API

class ExecutionLogItem(BaseModel):
    agent: str
    status: str

class SwarmResponse(BaseModel):
    status: str
    final_summary: str
    execution_log: List[ExecutionLogItem]
    results: Dict[str, Any]

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

    try:
        # Initialize the orchestrator
        # Note: In a production app, you'd pool this. For a hackathon, instantiating per request is fine.
        orchestrator = OrchestratorAgent(
            use_mock_scheduler=request.use_mock_scheduler,
            access_token=token
        )
        
        # Execute the swarm (this is async and might take 10-30 seconds)
        result = await orchestrator.execute(request.user_prompt)
        
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

    async def event_generator():
        orchestrator = OrchestratorAgent(
            use_mock_scheduler=request.use_mock_scheduler,
            access_token=token
        )
        try:
            async for chunk in orchestrator.execute_stream(request.user_prompt):
                # Yield in SSE format: data: {...}\n\n
                yield f"data: {chunk}\n\n"
        except Exception as e:
            error_msg = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_msg}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# --- Run Server Locally ---
if __name__ == "__main__":
    import uvicorn
    # Run on port 8000. Reload=True auto-restarts when you change code.
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)