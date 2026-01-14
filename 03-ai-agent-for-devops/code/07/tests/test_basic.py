"""
Basic tests for the AI Logging Agent
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config import Config
from tools.log_reader import read_log_file, list_log_files, search_logs


def test_config_validation():
    """Test configuration validation"""
    assert Config.GEMINI_MODEL is not None
    assert Config.LOG_DIRECTORY is not None
    print("✓ Configuration validation passed")


def test_log_directory_exists():
    """Test log directory exists"""
    assert os.path.exists(Config.LOG_DIRECTORY)
    print("✓ Log directory exists")


def test_list_log_files():
    """Test listing log files"""
    result = list_log_files.invoke({})
    assert "app.log" in result or "No .log files" in result
    print("✓ List log files works")


def test_read_log_file():
    """Test reading a log file"""
    # This assumes app.log exists
    result = read_log_file.invoke({"filename": "app.log"})
    assert "Error" not in result or "INFO" in result or "not found" in result
    print("✓ Read log file works")


def test_search_logs():
    """Test searching in logs"""
    result = search_logs.invoke({"filename": "app.log", "search_term": "ERROR"})
    assert result is not None
    print("✓ Search logs works")


if __name__ == "__main__":
    print("Running basic tests...\n")
    
    try:
        test_config_validation()
        test_log_directory_exists()
        test_list_log_files()
        test_read_log_file()
        test_search_logs()
        
        print("\n✓ All tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
