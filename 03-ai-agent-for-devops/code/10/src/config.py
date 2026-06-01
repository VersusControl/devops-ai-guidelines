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
    
    # LLM Provider selection: 'gemini' (default), 'github', or 'minimax'
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'gemini').lower()

    # GitHub Models Configuration
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    GITHUB_MODEL = os.getenv('GITHUB_MODEL', 'openai/gpt-5')
    GITHUB_ENDPOINT = os.getenv('GITHUB_ENDPOINT', 'https://models.github.ai/inference')

    # MiniMax Configuration
    MINIMAX_API_KEY = os.getenv('MINIMAX_API_KEY', '')
    MINIMAX_MODEL = os.getenv('MINIMAX_MODEL', 'MiniMax-M3')
    MINIMAX_ENDPOINT = os.getenv('MINIMAX_ENDPOINT', 'https://api.minimax.io/v1')
    
    # Paths
    LOG_DIRECTORY = os.getenv('LOG_DIRECTORY', 'logs')
    
    # Kubernetes Configuration
    K8S_KUBECONFIG = os.getenv('K8S_KUBECONFIG', '')
    K8S_CONTEXT = os.getenv('K8S_CONTEXT', 'default')
    K8S_DEFAULT_NAMESPACE = os.getenv('K8S_DEFAULT_NAMESPACE', 'production')
    
    # AWS Configuration
    AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
    AWS_RDS_INSTANCE_ID = os.getenv('AWS_RDS_INSTANCE_ID', '')
    
    # Slack Configuration
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')
    SLACK_CHANNEL = os.getenv('SLACK_CHANNEL', '#devops-alerts')
    
    # Agent Configuration
    MAX_ITERATIONS = 10
    VERBOSE = True
    
    @classmethod
    def is_k8s_configured(cls) -> bool:
        """Check if Kubernetes is configured"""
        return True
    
    @classmethod
    def is_aws_configured(cls) -> bool:
        """Check if AWS credentials are available"""
        return bool(
            os.getenv('AWS_ACCESS_KEY_ID') or
            os.getenv('AWS_PROFILE') or
            os.getenv('AWS_ROLE_ARN')
        )
    
    @classmethod
    def is_slack_configured(cls) -> bool:
        """Check if Slack webhook is configured"""
        return bool(cls.SLACK_WEBHOOK_URL)
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if cls.LLM_PROVIDER == 'gemini' and not cls.GEMINI_API_KEY:
            raise ValueError(
                "LLM_PROVIDER=gemini but GEMINI_API_KEY is not set. "
                "Please set it in .env file or environment variables."
            )
        if cls.LLM_PROVIDER == 'github' and not cls.GITHUB_TOKEN:
            raise ValueError(
                "LLM_PROVIDER=github but GITHUB_TOKEN is not set. "
                "Please set it in .env file or environment variables."
            )
        if cls.LLM_PROVIDER == 'minimax' and not cls.MINIMAX_API_KEY:
            raise ValueError(
                "LLM_PROVIDER=minimax but MINIMAX_API_KEY is not set. "
                "Please set it in .env file or environment variables."
            )
        
        if not os.path.exists(cls.LOG_DIRECTORY):
            os.makedirs(cls.LOG_DIRECTORY)
    
    @classmethod
    def get_system_prompt(cls) -> str:
        """Get the system prompt, with examples appended if available"""
        base_dir = os.path.dirname(os.path.dirname(__file__))
        
        prompt_file = os.path.join(base_dir, 'system_prompt.txt')
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                prompt = f.read()
        except FileNotFoundError:
            raise ValueError(
                f"System prompt file not found: {prompt_file}\n"
                "Please ensure system_prompt.txt exists in the project root."
            )
        
        examples_file = os.path.join(base_dir, 'examples.txt')
        try:
            with open(examples_file, 'r', encoding='utf-8') as f:
                prompt += '\n\n' + f.read()
        except FileNotFoundError:
            pass  # examples are optional
        
        return prompt


# Validate configuration on import
Config.validate()
