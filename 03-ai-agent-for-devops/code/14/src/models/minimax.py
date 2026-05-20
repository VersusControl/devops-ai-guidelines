"""
MiniMax LLM wrapper (OpenAI-compatible endpoint)
"""
from langchain_openai import ChatOpenAI
from ..config import Config


class MiniMaxModel:
    """Wrapper for MiniMax via OpenAI-compatible inference endpoint."""

    def __init__(self):
        # MiniMax requires temperature in (0.0, 1.0]
        temperature = max(Config.TEMPERATURE, 0.01)
        self.llm = ChatOpenAI(
            model=Config.MINIMAX_MODEL,
            api_key=Config.MINIMAX_API_KEY,
            base_url=Config.MINIMAX_ENDPOINT,
            temperature=temperature,
        )

    def get_llm(self):
        """Get the LLM instance"""
        return self.llm

    def get_llm_with_tools(self, tools: list):
        """Get LLM with tools bound"""
        return self.llm.bind_tools(tools)
