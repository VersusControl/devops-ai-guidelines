"""
Model factory — selects the LLM provider from the LLM_PROVIDER env variable.

Supported values:
  gemini   — Google Gemini (default)
  github   — GitHub Models (OpenAI-compatible endpoint)
  minimax  — MiniMax (OpenAI-compatible endpoint)
"""
from ..config import Config


def create_model():
    """
    Instantiate and return the configured LLM model.

    Reads LLM_PROVIDER from environment (via Config).
    Raises ValueError for unknown providers.
    """
    provider = Config.LLM_PROVIDER

    if provider == "gemini":
        from .gemini import GeminiModel
        return GeminiModel()

    if provider == "github":
        from .github_openai import GitHubModel
        return GitHubModel()

    if provider == "minimax":
        from .minimax import MiniMaxModel
        return MiniMaxModel()

    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. "
        "Supported values: gemini, github, minimax"
    )
