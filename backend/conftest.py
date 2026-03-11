"""
Pytest configuration - set test database before any app imports.
"""
import os
from pathlib import Path

# Load .env from backend/ so AZURE_OPENAI_* from .env are available
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

# Use in-memory SQLite for tests (must be set before app imports)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Dummy Azure OpenAI config when key is missing OR empty (GitHub Actions sets empty string for missing secrets)
if not os.environ.get("AZURE_OPENAI_API_KEY"):
    os.environ["AZURE_OPENAI_API_KEY"] = "test-key"
if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://test.openai.azure.com/"


def _is_dummy_azure_config() -> bool:
    """True when Azure OpenAI is not configured for real API calls."""
    key = os.environ.get("AZURE_OPENAI_API_KEY", "")
    return key in ("", "test-key")


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "llm: tests that require real Azure OpenAI (skipped when AZURE_OPENAI_API_KEY is dummy)",
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests marked 'llm' when Azure config is dummy."""
    if _is_dummy_azure_config():
        skip_llm = __import__("pytest").mark.skip(
            reason="Requires real AZURE_OPENAI_API_KEY (skipped in CI)"
        )
        for item in items:
            if "llm" in item.keywords:
                item.add_marker(skip_llm)
