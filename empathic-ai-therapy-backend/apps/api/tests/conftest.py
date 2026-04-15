"""
Shared pytest fixtures for the empathic-ai-therapy-backend test suite.
"""
import os
import sys

import pytest

# Ensure apps/api is on the path for all tests
_API_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _API_ROOT not in sys.path:
    sys.path.insert(0, _API_ROOT)

# Minimal env so Settings doesn't complain during collection
os.environ.setdefault("HUME_API_KEY", "test-hume-key")
os.environ.setdefault("HUME_SECRET_KEY", "test-hume-secret")
os.environ.setdefault("GCP_PROJECT", "test-project")
os.environ.setdefault("GCP_LOCATION", "us-central1")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_PASSWORD", "test")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")


@pytest.fixture()
def session_id() -> str:
    return "sess_test123"


@pytest.fixture()
def message_id() -> str:
    return "msg_abc456"
