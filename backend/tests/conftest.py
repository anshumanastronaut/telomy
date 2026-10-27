"""Test isolation for the backend suite.

On a machine that has a real account in ``./data/accounts.db`` (any dev who has ever signed in),
``accounts.enabled()`` flips the whole API into multi-user mode and every data route answers
"Please sign in." — failing ~95 tests that were written for single-user mode. The tests isolate
``TELOMY_DB`` (the health-data file) but not ``TELOMY_DATA_DIR`` (where the accounts store lives),
so they inherit the developer's real accounts.

Pointing ``TELOMY_DATA_DIR`` at a fresh empty directory for the whole session — set before the app
is imported — keeps the suite in single-user mode regardless of the developer's local ``./data``.
Modules that test multi-user behaviour create their own accounts in this clean store.
"""
import os
import tempfile

# Set before any ``from app...`` import so accounts.enabled() reads an empty store from the start.
os.environ.setdefault("TELOMY_DATA_DIR", tempfile.mkdtemp(prefix="telomy-test-accts-"))

# Pin "today" before any module imports app.seed. ``seed.TODAY`` is bound once at import from
# TELOMY_TODAY; a module setting it at its own import loses the race when another module imported
# app.seed first (binding it to the real date). That shifts the seeded therapy sessions' recency
# and flips the n-of-1 verdict in ``test_therapy_verdicts_match_seeded_truth`` — pass-alone,
# fail-in-suite. Fixing it here makes "today" deterministic for the whole session.
os.environ.setdefault("TELOMY_TODAY", "2026-10-06")
