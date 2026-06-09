import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from agents.base_agent import BaseAgent

class TestAgent(BaseAgent):
    """Test implementation of BaseAgent"""
    
    async def execute(self, task):
        self.log_action(f"Executing task: {task.get('name', 'unnamed')}")
        return {"status": "success", "task": task}

async def test_base_agent_initialization():
    """Test agent initialization"""
    agent = TestAgent(name="TestAgent", role="Test Role")
    
    assert agent.name == "TestAgent"
    assert agent.role == "Test Role"
    assert agent.conversation_history == []
    print("✓ Agent initialization test passed")

async def test_base_agent_logging():
    """Test agent logging"""
    agent = TestAgent(name="TestAgent", role="Test Role")
    
    # Should not raise exception
    agent.log_action("Test action")
    agent.log_action("Error action", level="ERROR")
    print("✓ Agent logging test passed")

async def test_base_agent_history():
    """Test conversation history"""
    agent = TestAgent(name="TestAgent", role="Test Role")
    
    agent.add_to_history("user", "Hello")
    agent.add_to_history("assistant", "Hi there")
    
    assert len(agent.conversation_history) == 2
    assert agent.conversation_history[0]["role"] == "user"
    print("✓ Agent history test passed")

async def test_base_agent_stats():
    """Test agent statistics"""
    agent = TestAgent(name="TestAgent", role="Test Role")
    
    stats = agent.get_stats()
    
    assert stats["name"] == "TestAgent"
    assert stats["role"] == "Test Role"
    assert "created_at" in stats
    print("✓ Agent stats test passed")

async def test_base_agent_execute():
    """Test agent execution"""
    agent = TestAgent(name="TestAgent", role="Test Role")
    
    task = {"name": "test_task", "data": "test_data"}
    result = await agent.execute(task)
    
    assert result["status"] == "success"
    assert result["task"] == task
    print("✓ Agent execution test passed")

async def run_all_tests():
    """Run all base agent tests"""
    print("\n=== Running Base Agent Tests ===\n")
    
    await test_base_agent_initialization()
    await test_base_agent_logging()
    await test_base_agent_history()
    await test_base_agent_stats()
    await test_base_agent_execute()
    
    print("\n✅ All Base Agent tests passed!\n")

if __name__ == "__main__":
    asyncio.run(run_all_tests())