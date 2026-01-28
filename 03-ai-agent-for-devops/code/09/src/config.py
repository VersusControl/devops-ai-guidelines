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
    
    # Kubernetes Configuration
    K8S_KUBECONFIG = os.getenv('K8S_KUBECONFIG', '')
    K8S_CONTEXT = os.getenv('K8S_CONTEXT', 'default')
    K8S_DEFAULT_NAMESPACE = os.getenv('K8S_DEFAULT_NAMESPACE', 'production')
    
    # Agent Configuration
    MAX_ITERATIONS = 5
    VERBOSE = True
    
    @classmethod
    def is_k8s_configured(cls) -> bool:
        """Check if Kubernetes is configured"""
        # For placeholder mode, always return True
        return True
    
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
    
    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the system prompt for the agent"""
        prompt_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'system_prompt.txt'
        )
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise ValueError(
                f"System prompt file not found: {prompt_file}\n"
                "Please ensure system_prompt.txt exists in the project root."
            )


# Validate configuration on import
Config.validate()
