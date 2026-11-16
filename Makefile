.PHONY: setup lint typecheck check ingest status clean

setup:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

lint:
	.venv/bin/ruff check pipeline/ api/ --fix
	.venv/bin/ruff format pipeline/ api/

typecheck:
	.venv/bin/mypy pipeline/ api/

check: lint typecheck

ingest:
	.venv/bin/python -m pipeline ingest $(ARGS)

status:
	.venv/bin/python -m pipeline status

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -f .progress_*.json .llm_progress.json
