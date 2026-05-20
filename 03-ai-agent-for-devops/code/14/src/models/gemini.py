"""
Google Gemini LLM wrapper
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from ..config import Config


class GeminiModel:
    """Wrapper for Google Gemini LLM"""
    
    def __init__(self):
        """Initialize the Gemini model"""
        self.llm = ChatGoogleGenerativeAI(
            model=Config.GEMINI_MODEL,
            google_api_key=Config.GEMINI_API_KEY,
            temperature=Config.TEMPERATURE
        )
    
    def get_llm(self):
        """Get the LLM instance"""
        return self.llm
    
    def get_llm_with_tools(self, tools: list):
        """Get LLM with tools bound"""
        return self.llm.bind_tools(tools)
