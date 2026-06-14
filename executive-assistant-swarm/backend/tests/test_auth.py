import sys
import os

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from api.main import app, memory_db

client = TestClient(app)

def test_auth_forgot_reset_flow():
    """Test the complete registration, forgot password, reset password, and login flow."""
    print("\n--- Starting Auth and Password Reset Integration Tests ---")
    
    username = "test_reset_user"
    email = "test_reset@example.com"
    old_password = "password123"
    new_password = "newpassword456"
    
    # 1. Clean up user if they already exist from a previous run
    memory_db.delete_password_reset(username)
    # We will delete the user manually in the DB if they exist to keep the test clean
    with memory_db._get_connection() as conn:
        with conn:
            conn.cursor().execute("DELETE FROM users WHERE username = ?", (username,))
            
    # 2. Register new user
    print("Step 1: Registering user...")
    register_payload = {
        "username": username,
        "password": old_password,
        "email": email
    }
    response = client.post("/auth/register", json=register_payload)
    assert response.status_code == 200, f"Registration failed: {response.text}"
    register_data = response.json()
    assert "access_token" in register_data
    assert register_data["user"]["username"] == username
    assert register_data["user"]["email"] == email
    print("[OK] Registration successful!")
    
    # 3. Request password reset with correct details
    print("Step 2: Requesting forgot-password...")
    forgot_payload = {
        "username": username,
        "email": email
    }
    response = client.post("/auth/forgot-password", json=forgot_payload)
    assert response.status_code == 200, f"Forgot password request failed: {response.text}"
    print("[OK] Forgot password code generated and logged!")
    
    # 4. Retrieve code from MemoryDB
    reset_entry = memory_db.get_password_reset(username)
    assert reset_entry is not None, "Failed to find password reset entry in database"
    code = reset_entry["code"]
    print(f"[OK] Retrieved reset code from DB: {code}")
    
    # 5. Reset password using the code
    print("Step 3: Resetting password...")
    reset_payload = {
        "username": username,
        "code": code,
        "new_password": new_password
    }
    response = client.post("/auth/reset-password", json=reset_payload)
    assert response.status_code == 200, f"Reset password failed: {response.text}"
    print("[OK] Password reset successful!")
    
    # 6. Verify old password no longer works
    print("Step 4: Attempting login with old password...")
    login_payload_old = {
        "username": username,
        "password": old_password
    }
    response = client.post("/auth/login", json=login_payload_old)
    assert response.status_code == 401, "Login with old password should have failed"
    print("[OK] Login with old password rejected (401) as expected!")
    
    # 7. Verify login with new password works
    print("Step 5: Logging in with new password...")
    login_payload_new = {
        "username": username,
        "password": new_password
    }
    response = client.post("/auth/login", json=login_payload_new)
    assert response.status_code == 200, f"Login with new password failed: {response.text}"
    login_data = response.json()
    assert "access_token" in login_data
    print("[OK] Login with new password successful!")
    
    # Clean up test user
    with memory_db._get_connection() as conn:
        with conn:
            conn.cursor().execute("DELETE FROM users WHERE username = ?", (username,))
    print("[OK] Test user cleaned up successfully!")

if __name__ == "__main__":
    test_auth_forgot_reset_flow()
    print("\n[OK] ALL AUTH INTEGRATION TESTS PASSED!")
