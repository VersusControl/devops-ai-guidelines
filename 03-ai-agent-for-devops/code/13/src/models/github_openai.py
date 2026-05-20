"""
GitHub Models LLM wrapper (OpenAI-compatible endpoint)
"""
from langchain_openai import ChatOpenAI
from ..config import Config


class GitHubModel:
    """Wrapper for GitHub Models via OpenAI-compatible inference endpoint."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=Config.GITHUB_MODEL,
            api_key=Config.GITHUB_TOKEN,
            base_url=Config.GITHUB_ENDPOINT,
            temperature=Config.TEMPERATURE,
        )

    def get_llm(self):
        """Get the LLM instance"""
        return self.llm

    def get_llm_with_tools(self, tools: list):
        """Get LLM with tools bound"""
        return self.llm.bind_tools(tools)
