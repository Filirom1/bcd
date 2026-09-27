# TODO — Code Quality and Formatting

- [x] Fix Ruff, Black, and other configured Python code-quality issues throughout the project. Ruff and Black now pass cleanly for `src/` and `tests/`, and the fast unified test suite passes.
- [x] Add a CI guard that runs Ruff and Black checks so formatting and lint regressions fail CI.

## Verification commands

```bash
ruff check src/ tests/
black --check src/ tests/
python run_tests.py all --fast
```
