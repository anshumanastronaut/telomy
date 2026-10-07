"""Runtime configuration. Values come from the environment, optionally loaded from backend/.env (never committed).

  ANTHROPIC_API_KEY  enables Claude for Sinc answers (otherwise the grounded retrieval composer is used)
  TELOMY_DB          SQLite path (default backend/telomy.db)
  TELOMY_TODAY       pins "today" for the seeded test profile (e.g. 2026-10-06) so demos and tests are reproducible
  TELOMY_ADMIN_KEY   protects device-key management endpoints (default "dev-admin" for local development only)
"""
import os

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:  # python-dotenv is optional at runtime
    pass

ADMIN_KEY = os.environ.get("TELOMY_ADMIN_KEY", "dev-admin")
