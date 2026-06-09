import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from api.main import app

# Create the test client
client = TestClient(app)

def test_root_endpoint():
    """Test the root endpoint."""
    print("\n--- Testing Root Endpoint ---")
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    print(f"✅ Root endpoint works: {data['message']}")

def test_health_check():
    """Test the health check endpoint."""
    print("\n--- Testing Health Check ---")
    response = client.get("/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("✅ Health check passed")

def test_execute_swarm():
    """Test the main execution endpoint."""
    print("\n--- Testing Swarm Execution Endpoint ---")
    
    # The Golden Path Demo Prompt
    payload = {
        "user_prompt": "I have a strategy meeting with Contoso next week. Research their latest AI product launches and generate a prep briefing.",
        "use_mock_scheduler": True  # Using mock so it doesn't hang on Graph API
    }
    
    print("Sending prompt to API... (This will take 15-30 seconds)")
    response = client.post("/execute", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ API Execution Successful!")
        print(f"   Status: {data['status']}")
        print(f"   Agents Executed: {len(data['execution_log'])}")
        print(f"   Summary Preview: {data['final_summary'][:100]}...")
    else:
        print(f"❌ API Execution Failed: {response.status_code}")
        print(f"   Error: {response.json().get('detail')}")
        assert False, "API execution failed"

if __name__ == "__main__":
    print("="*50)
    print("RUNNING API TESTS")
    print("="*50)
    
    test_root_endpoint()
    test_health_check()
    test_execute_swarm()
    
    print("\n" + "="*50)
    print("🎉 ALL API TESTS PASSED!")
    print("="*50)