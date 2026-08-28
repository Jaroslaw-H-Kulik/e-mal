
  Run the whole test suite (Layer 0 smoke tests today, Layer 1 golden-master tests later):
  python -m uv run pytest

  Verbose (see each test by name):
  python -m uv run pytest -v

  Run just one file:
  python -m uv run pytest tests/test_smoke.py -v

  Run one test by name:
  python -m uv run pytest -k test_server_serves_sandboxed_state -v

  Stop at the first failure:
  python -m uv run pytest -x

  Layer 2 — run invariant checks against your real data:
  python -m uv run python tests/invariants.py

  Run invariant checks against a different snapshot (e.g. a sandboxed copy, or an old backup):
  python -m uv run python tests/invariants.py data/genealogy_new_model.backup.json

  Install/sync dependencies (if pyproject.toml/uv.lock ever change, e.g. after a git pull):
  python -m uv sync