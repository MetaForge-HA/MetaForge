.PHONY: check test ci fix lint format typecheck unit contract integration dashboard-check

# Level 0: Static analysis (before every commit)
check: lint format typecheck

lint:
	ruff check .

format:
	ruff format --check .

typecheck:
	mypy --strict .

# Level 1-2: Unit + contract tests (before every PR)
test: unit contract

unit:
	pytest tests/unit/ -x --tb=short -q

contract:
	pytest tests/contract/ -v --tb=short

# Level 3: Integration tests
integration:
	pytest tests/integration/ -v --timeout=120

# Everything: check + test + integration (before merge)
ci: check test integration

# Auto-fix: ruff check --fix + ruff format
fix:
	ruff check --fix .
	ruff format .

# Dashboard type check
dashboard-check:
	cd dashboard && npx tsc --noEmit
