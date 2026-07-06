# Contributing

## Setup

```bash
git clone https://github.com/ck-rajput/mcp-resilient
cd mcp-resilient
pip install -e ".[dev,cli]"
pre-commit install
```

## Before opening a PR

```bash
pytest -q                 # all tests must pass
ruff check src tests       # lint
ruff format src tests      # format
mypy src                   # type check
```

## Project conventions

- New feature → new file under the relevant subpackage (`retry/`,
  `circuit_breaker/`, `fallback/`, `observability/`, `storage/`), not a patch
  to an existing module, unless it's a bug fix.
- Every public function/class needs a docstring explaining _why_, not just
  _what_ — see existing modules for the expected level of detail.
- New behavior needs a test in the matching `tests/test_*.py` file.
- Update `CHANGELOG.md` under `[Unreleased]`.

## Reporting bugs

Open a GitHub issue with: Python version, `mcp-resilient` version, minimal
repro, and expected vs. actual behavior.
