"""
Unit tests for MiniMax LLM provider integration.
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from importlib import reload

# Add parent directory to path so we can import the src module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def _reload_all():
    """Reload config and model modules to pick up env var changes."""
    import src.config
    reload(src.config)
    import src.models.minimax
    reload(src.models.minimax)
    import src.models.factory
    reload(src.models.factory)
    import src.models
    reload(src.models)


class TestMiniMaxModel(unittest.TestCase):
    """Tests for MiniMaxModel class."""

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'MINIMAX_MODEL': 'MiniMax-M2.7',
        'MINIMAX_ENDPOINT': 'https://api.minimax.io/v1',
        'TEMPERATURE': '0.5',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_model_init(self, mock_chat):
        """MiniMaxModel initializes ChatOpenAI with correct params."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        mock_chat.assert_called_once_with(
            model='MiniMax-M2.7',
            api_key='test-key-123',
            base_url='https://api.minimax.io/v1',
            temperature=0.5,
        )

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'TEMPERATURE': '0.0',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_temperature_clamping(self, mock_chat):
        """MiniMax clamps temperature=0.0 to 0.01."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        call_kwargs = mock_chat.call_args[1]
        self.assertAlmostEqual(call_kwargs['temperature'], 0.01)

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'TEMPERATURE': '0.7',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_temperature_passthrough(self, mock_chat):
        """Non-zero temperature passes through unchanged."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        call_kwargs = mock_chat.call_args[1]
        self.assertAlmostEqual(call_kwargs['temperature'], 0.7)

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'TEMPERATURE': '0.3',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_get_llm(self, mock_chat):
        """get_llm() returns the underlying LLM instance."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        llm = model.get_llm()
        self.assertIs(llm, mock_chat.return_value)

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'TEMPERATURE': '0.3',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_get_llm_with_tools(self, mock_chat):
        """get_llm_with_tools() binds tools to the LLM."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        mock_llm = mock_chat.return_value
        mock_bound = MagicMock()
        mock_llm.bind_tools.return_value = mock_bound

        model = MiniMaxModel()
        tools = [MagicMock(), MagicMock()]
        result = model.get_llm_with_tools(tools)

        mock_llm.bind_tools.assert_called_once_with(tools)
        self.assertIs(result, mock_bound)

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_default_model(self, mock_chat):
        """Default model is MiniMax-M3."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs['model'], 'MiniMax-M3')

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'MINIMAX_MODEL': 'MiniMax-M2.7-highspeed',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_custom_model(self, mock_chat):
        """Custom model name from env is used."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs['model'], 'MiniMax-M2.7-highspeed')

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_default_endpoint(self, mock_chat):
        """Default endpoint is https://api.minimax.io/v1."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs['base_url'], 'https://api.minimax.io/v1')

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'MINIMAX_ENDPOINT': 'https://custom.endpoint.com/v1',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_custom_endpoint(self, mock_chat):
        """Custom endpoint from env is used."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        call_kwargs = mock_chat.call_args[1]
        self.assertEqual(call_kwargs['base_url'], 'https://custom.endpoint.com/v1')

    @patch.dict(os.environ, {
        'MINIMAX_API_KEY': 'test-key-123',
        'TEMPERATURE': '1.0',
        'LLM_PROVIDER': 'minimax',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_minimax_max_temperature(self, mock_chat):
        """Temperature=1.0 passes through (max allowed)."""
        _reload_all()
        from src.models.minimax import MiniMaxModel

        model = MiniMaxModel()
        call_kwargs = mock_chat.call_args[1]
        self.assertAlmostEqual(call_kwargs['temperature'], 1.0)


class TestModelFactory(unittest.TestCase):
    """Tests for the model factory with MiniMax provider."""

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_factory_creates_minimax(self, mock_chat):
        """create_model() returns MiniMaxModel when LLM_PROVIDER=minimax."""
        _reload_all()
        from src.models.factory import create_model
        from src.models.minimax import MiniMaxModel

        model = create_model()
        self.assertIsInstance(model, MiniMaxModel)

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'unknown_provider',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    def test_factory_rejects_unknown(self):
        """create_model() raises ValueError for unknown providers."""
        _reload_all()
        from src.models.factory import create_model

        with self.assertRaises(ValueError) as ctx:
            create_model()
        self.assertIn('minimax', str(ctx.exception).lower())

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_factory_minimax_has_get_llm(self, mock_chat):
        """Factory-created MiniMax model has get_llm method."""
        _reload_all()
        from src.models.factory import create_model

        model = create_model()
        self.assertTrue(hasattr(model, 'get_llm'))

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    @patch('langchain_openai.ChatOpenAI')
    def test_factory_minimax_has_get_llm_with_tools(self, mock_chat):
        """Factory-created MiniMax model has get_llm_with_tools method."""
        _reload_all()
        from src.models.factory import create_model

        model = create_model()
        self.assertTrue(hasattr(model, 'get_llm_with_tools'))


class TestConfigValidation(unittest.TestCase):
    """Tests for Config validation with MiniMax provider."""

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': '',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    def test_validate_minimax_missing_key(self):
        """Config.validate() raises when MINIMAX_API_KEY is empty."""
        import src.config
        with self.assertRaises(ValueError) as ctx:
            reload(src.config)
        self.assertIn('MINIMAX_API_KEY', str(ctx.exception))

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    def test_validate_minimax_with_key(self):
        """Config.validate() passes when MINIMAX_API_KEY is set."""
        _reload_all()
        from src.config import Config
        self.assertEqual(Config.LLM_PROVIDER, 'minimax')

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'MINIMAX_MODEL': 'MiniMax-M3',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    def test_config_minimax_defaults(self):
        """Config has correct MiniMax default values."""
        _reload_all()
        from src.config import Config

        self.assertEqual(Config.MINIMAX_ENDPOINT, 'https://api.minimax.io/v1')
        self.assertEqual(Config.MINIMAX_MODEL, 'MiniMax-M3')

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    def test_config_minimax_provider_value(self):
        """Config.LLM_PROVIDER is 'minimax' when set."""
        _reload_all()
        from src.config import Config
        self.assertEqual(Config.LLM_PROVIDER, 'minimax')


class TestModelExports(unittest.TestCase):
    """Tests for models package __init__ exports."""

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    def test_minimax_model_importable(self):
        """MiniMaxModel is importable from src.models."""
        _reload_all()
        from src.models import MiniMaxModel
        self.assertIsNotNone(MiniMaxModel)

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    def test_create_model_importable(self):
        """create_model is importable from src.models."""
        _reload_all()
        from src.models import create_model
        self.assertIsNotNone(create_model)

    @patch.dict(os.environ, {
        'LLM_PROVIDER': 'minimax',
        'MINIMAX_API_KEY': 'test-key-123',
        'LOG_DIRECTORY': '/tmp/test-logs',
    })
    def test_minimax_in_all(self):
        """MiniMaxModel is listed in __all__."""
        _reload_all()
        from src import models
        self.assertIn('MiniMaxModel', models.__all__)


if __name__ == '__main__':
    unittest.main()
