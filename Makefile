SHELL := /bin/bash
PY := .venv/bin/python
PNPM := bash scripts/pnpm
export PHILANTHRA_ENV ?= demo
export UV_CACHE_DIR := $(CURDIR)/.cache/uv

.PHONY: doctor setup demo dev check test test-e2e build smoke verify reset-demo stop migrate seed api-client backup restore-test audit
doctor:
	python3 scripts/doctor.py
setup:
	bash scripts/setup.sh
demo:
	python3 scripts/runtime.py demo
dev:
	python3 scripts/runtime.py dev
stop:
	python3 scripts/runtime.py stop
migrate:
	$(PY) apps/api/manage.py migrate --noinput
seed:
	$(PY) apps/api/manage.py seed_demo
check:
	.venv/bin/ruff check apps/api tests scripts
	.venv/bin/ruff format --check apps/api tests scripts
	.venv/bin/mypy apps/api/philanthra/analytics apps/api/philanthra/ingestion
	$(PY) apps/api/manage.py check
	$(PY) apps/api/manage.py makemigrations --check --dry-run
	$(PNPM) format:check
	$(PNPM) check
	$(PY) scripts/generate_contract.py --check
test:
	.venv/bin/pytest -q --cov=philanthra --cov-branch --cov-report=term-missing --cov-report=xml
	$(PNPM) test
test-e2e:
	$(PNPM) test:e2e
build:
	$(PNPM) build
smoke:
	$(PY) scripts/e2e-server.py --smoke
verify: check test build test-e2e smoke
api-client:
	$(PY) scripts/generate_contract.py
reset-demo:
	bash scripts/reset-demo.sh "$(CONFIRM)"
backup:
	$(PY) scripts/backup.py create
restore-test:
	$(PY) scripts/backup.py verify
audit:
	$(PY) scripts/audit.py
