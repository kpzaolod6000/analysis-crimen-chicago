"""Shared config for the E2E suite (base URL overridable por env)."""

import os

BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:5173")
