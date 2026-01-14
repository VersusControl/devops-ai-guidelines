"""
Configuration management for the AI Logging Agent
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Application configuration"""
    
    # API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.1'))
    
    # Paths
    LOG_DIRECTORY = os.getenv('LOG_DIRECTORY', 'logs')
    
    # Agent Configuration
    MAX_ITERATIONS = 5
    VERBOSE = True
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.GEMINI_API_KEY:
            raise ValueError(
                "GEMINI_API_KEY not found. "
                "Please set it in .env file or environment variables."
            )
        
        if not os.path.exists(cls.LOG_DIRECTORY):
            os.makedirs(cls.LOG_DIRECTORY)
            print(f"Created log directory: {cls.LOG_DIRECTORY}")
    
    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the system prompt for the agent"""
        return """You are a DevOps expert specializing in log analysis.

Your responsibilities:
- Analyze application logs to identify errors, warnings, and patterns
- Explain technical issues in clear, concise language
- Identify root causes and relationships between events
- Provide actionable insights

Your limitations:
- You can only read and analyze logs, not modify them
- You cannot take actions like restarting services or modifying configurations
- You work with the log files available in the logs directory

Be direct and helpful. Focus on what's actually in the logs, not speculation."""


# Validate configuration on import
Config.validate()
