import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.config import settings

def test_settings_loaded():
    """Test that settings are loaded from .env file"""
    assert settings.AZURE_OPENAI_ENDPOINT != "", "AZURE_OPENAI_ENDPOINT not set"
    assert settings.AZURE_OPENAI_API_KEY != "", "AZURE_OPENAI_API_KEY not set"
    print("✓ Settings loaded successfully")

def test_settings_validation():
    """Test settings validation"""
    # This will fail if .env is not properly configured
    is_valid = settings.validate()
    if is_valid:
        print("✓ All required settings are configured")
    else:
        print("⚠ Warning: Some settings may be missing")
    assert is_valid, "Settings validation failed"

if __name__ == "__main__":
    test_settings_loaded()
    test_settings_validation()
    print("\n✅ All configuration tests passed!")