"""
Integration tests for MiniMax LLM provider.

These tests verify end-to-end behavior against the real MiniMax API.
They are skipped if MINIMAX_API_KEY is not set in the environment.

Run with:
    MINIMAX_API_KEY=your_key python -m pytest tests/test_minimax_integration.py -v
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SKIP_REASON = "MINIMAX_API_KEY not set — skipping integration tests"


@unittest.skipUnless(os.getenv('MINIMAX_API_KEY'), SKIP_REASON)
class TestMiniMaxIntegration(unittest.TestCase):
    """Integration tests against live MiniMax API."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault('LLM_PROVIDER', 'minimax')
        os.environ.setdefault('MINIMAX_MODEL', 'MiniMax-M2.7')
        os.environ.setdefault('LOG_DIRECTORY', '/tmp/test-logs')
        os.makedirs('/tmp/test-logs', exist_ok=True)

        from importlib import reload
        import src.config
        reload(src.config)

    def test_minimax_chat_completion(self):
        """MiniMax can produce a basic chat completion."""
        from src.models.minimax import MiniMaxModel
        model = MiniMaxModel()
        llm = model.get_llm()
        response = llm.invoke("Say hello in one word.")
        self.assertTrue(len(response.content) > 0)

    def test_minimax_tool_binding(self):
        """MiniMax model accepts tool bindings."""
        from langchain_core.tools import tool

        @tool
        def get_time() -> str:
            """Get the current time."""
            return "12:00 PM"

        from src.models.minimax import MiniMaxModel
        model = MiniMaxModel()
        llm_with_tools = model.get_llm_with_tools([get_time])
        response = llm_with_tools.invoke("What time is it?")
        # Response should have content or tool_calls
        self.assertTrue(
            response.content or getattr(response, 'tool_calls', None)
        )

    def test_factory_minimax_integration(self):
        """Factory creates a working MiniMax model."""
        from src.models.factory import create_model
        model = create_model()
        llm = model.get_llm()
        response = llm.invoke("Reply with just the word 'ok'.")
        self.assertTrue(len(response.content) > 0)


if __name__ == '__main__':
    unittest.main()
