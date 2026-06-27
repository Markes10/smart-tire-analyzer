.PHONY: help install backend frontend test lint clean

# Cross-platform dev launcher. On Windows, prefer run_services.bat which
# opens two visible terminal windows; this Makefile is best for git-bash,
# WSL, macOS, and Linux.

PY     ?= .venv/bin/python
PIP    ?= $(PY) -m pip
NPM    ?= npm
UVICORN := $(PY) -m uvicorn

REPO_ROOT := $(shell pwd)
export PYTHONPATH := $(REPO_ROOT):$(REPO_ROOT)/backend

help:
	@echo "Targets:"
	@echo "  make install        - create venv + install deps"
	@echo "  make backend        - start FastAPI backend on :8000"
	@echo "  make frontend       - start Next.js dev server on :3000"
	@echo "  make test           - run pytest"
	@echo "  make lint           - run ruff"
	@echo "  make certs          - generate dev TLS certificates"
	@echo "  make certs-prod     - guide for production TLS setup"
	@echo "  make clean          - remove caches"

install:
	@test -d .venv || python -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt
	cd frontend && $(NPM) ci --no-audit --no-fund

backend:
	cd backend && $(UVICORN) app.main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	cd frontend && $(NPM) run dev

test:
	$(PY) -m pytest tests/ -v --tb=short

lint:
	$(PY) -m ruff check backend/app utils tests --select E,F,W,I

certs:
	sh scripts/generate_dev_certs.sh

certs-prod:
	@echo "For production TLS, run:"
	@echo "  bash scripts/setup_production_certs.sh your-domain.com"
	@echo ""
	@echo "See deployment/docker/nginx.conf and scripts/setup_production_certs.sh"
	@echo "for detailed setup instructions."

clean:
	rm -rf .pytest_cache .mypy_cache frontend/.next frontend/tsconfig.tsbuildinfo
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
