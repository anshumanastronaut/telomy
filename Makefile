# Telomy developer commands — run `make help`
PY := backend/.venv/bin/python
export TELOMY_TODAY ?= 2026-10-06

.PHONY: help setup voice seed api mobile test test-backend test-mobile docs clean

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

setup: ## Create venv, install backend + mobile deps, create backend/.env
	python3.13 -m venv backend/.venv || python3 -m venv backend/.venv
	$(PY) -m pip install -q --upgrade pip && $(PY) -m pip install -q -r backend/requirements.txt
	cd mobile && npm install
	@test -f backend/.env || cp backend/.env.example backend/.env
	@echo "✓ setup done — next: make seed && make api"

voice: ## Install local Whisper for Sinc voice (optional, large)
	$(PY) -m pip install -q -r backend/requirements-voice.txt

seed: ## Rebuild the fictitious test Vault
	rm -f backend/telomy.db && cd backend && .venv/bin/python -m app.seed

api: ## Run the API on :8787
	cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8787 --reload

mobile: ## Start the Expo dev server
	cd mobile && npx expo start

test: test-backend test-mobile ## Run all checks

test-backend:
	cd backend && .venv/bin/python -m pytest -q

test-mobile:
	cd mobile && npx tsc --noEmit

docs: ## Regenerate docs/API.md and docs/DATA_MODEL.md
	$(PY) scripts/gen_docs.py

clean:
	rm -rf backend/.pytest_cache backend/**/__pycache__
