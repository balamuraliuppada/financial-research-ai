"""
conftest.py
-----------
Shared pytest fixtures for the Financial Research AI backend test suite.
Sets environment overrides BEFORE importing the app to avoid side effects.
"""
import os
import pytest

# ── Set env overrides before any app import ───────────────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("API_KEY", "")           # auth disabled in tests by default
os.environ.setdefault("GOOGLE_API_KEY", "")    # prevents agent from crashing on import
os.environ.setdefault("REDIS_URL", "")         # cache gracefully disabled in tests

from fastapi.testclient import TestClient

# Import app after env is set
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.main import app


@pytest.fixture(scope="session")
def client():
    """FastAPI TestClient shared across all tests in a session."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_client():
    """TestClient with API_KEY auth enabled for auth-related tests."""
    import backend.main as main_module
    os.environ["API_KEY"] = "test-secret"
    main_module._API_KEY = "test-secret"
    with TestClient(app) as c:
        yield c
    os.environ["API_KEY"] = ""
    main_module._API_KEY = ""
