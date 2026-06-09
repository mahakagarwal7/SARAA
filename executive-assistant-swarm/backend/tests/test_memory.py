import sys
import os
import pytest

# Add backend to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.memory_db import MemoryDB

def test_memory_preferences():
    # Use a separate db for testing
    db = MemoryDB(db_name="test_memory.db")
    
    # Save a preference
    db.save_preference("user_123", "communication_style", "bullet points")
    db.save_preference("user_123", "communication_style", "concise bullet points") # Overwrite
    db.save_preference("user_123", "schedule", "no fridays")
    
    # Get preferences
    prefs = db.get_preferences("user_123")
    
    assert prefs["communication_style"] == "concise bullet points"
    assert prefs["schedule"] == "no fridays"

def test_memory_briefings():
    db = MemoryDB(db_name="test_memory.db")
    
    # Save a briefing
    db.save_briefing("Test Meeting 1", "This is the first meeting briefing.")
    db.save_briefing("Test Meeting 2", "This is the second meeting briefing.")
    
    # Get past briefings
    briefings = db.get_past_briefings(limit=1)
    
    assert len(briefings) == 1
    assert briefings[0]["subject"] == "Test Meeting 2"
    
def teardown_module(module):
    """Clean up the test db after tests run."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_db_path = os.path.join(base_dir, "test_memory.db")
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

if __name__ == "__main__":
    test_memory_preferences()
    test_memory_briefings()
    teardown_module(None)
    print("✅ All MemoryDB tests passed!")
