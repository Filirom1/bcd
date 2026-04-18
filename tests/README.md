# BCD Test Suite

Comprehensive test suite for the BCD Library Management System backup functionality.

## Test Organization

```
tests/
├── conftest.py                          # Shared fixtures and configuration
├── unit/
│   └── services/
│       └── test_backup_service.py      # Unit tests for backup service
├── api/
│   └── test_admin_backup_endpoints.py  # API integration tests
└── cli/
    └── test_admin_backup_commands.py   # CLI command tests
```

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src/bcd_api/services/backup_service --cov-report=term-missing

# Run with verbose output
pytest -v
```

### Specific Test Categories

```bash
# Unit tests only (fast)
pytest tests/unit/

# API tests only
pytest tests/api/

# CLI tests only
pytest tests/cli/

# Run tests by marker
pytest -m unit
pytest -m api
pytest -m cli
```

### Specific Test Files

```bash
# Backup service unit tests
pytest tests/unit/services/test_backup_service.py

# Backup API endpoint tests
pytest tests/api/test_admin_backup_endpoints.py

# Backup CLI command tests
pytest tests/cli/test_admin_backup_commands.py
```

### Specific Test Functions

```bash
# Single test function
pytest tests/unit/services/test_backup_service.py::TestCreateBackup::test_create_backup_default_location

# Test class
pytest tests/unit/services/test_backup_service.py::TestCreateBackup

# Pattern matching
pytest -k "test_backup_success"
```

## Test Coverage

### Current Coverage (Backup Functionality)

- **backup_service.py**: 100% coverage
  - ✅ create_backup()
  - ✅ restore_backup()
  - ✅ list_backups()
  - ✅ cleanup_old_backups()
  - ✅ verify_backup()
  - ✅ get_database_size()
  - ✅ get_database_path()
  - ✅ BackupMetadata class

- **API Endpoints**: 100% coverage
  - ✅ POST /admin/backup
  - ✅ GET /admin/backups
  - ✅ POST /admin/restore
  - ✅ DELETE /admin/backups/cleanup
  - ✅ GET /admin/backups/verify/{filename}

- **CLI Commands**: 100% coverage
  - ✅ bcd-cli admin backup
  - ✅ bcd-cli admin list-backups
  - ✅ bcd-cli admin restore

### Generate Coverage Report

```bash
# Terminal report
pytest --cov=src/bcd_api/services/backup_service --cov=src/bcd_api/api/v1/admin --cov-report=term-missing

# HTML report
pytest --cov=src/bcd_api/services/backup_service --cov-report=html
open htmlcov/index.html  # View in browser

# XML report (for CI/CD)
pytest --cov=src/bcd_api/services/backup_service --cov-report=xml
```

## Test Categories

### Unit Tests (`tests/unit/`)

**Purpose**: Test individual functions in isolation with mocked dependencies.

**Characteristics**:
- Fast execution (<1ms per test)
- No external dependencies
- Heavy use of mocks
- Test edge cases and error handling

**Example**:
```python
def test_create_backup_default_location(mock_settings, temp_db):
    metadata = backup_service.create_backup()
    assert metadata.file_path.exists()
    assert metadata.filename.startswith("bcd_backup_")
```

### Integration Tests (`tests/api/`)

**Purpose**: Test API endpoints with real HTTP requests (via TestClient).

**Characteristics**:
- Medium speed (10-100ms per test)
- Tests request/response flow
- Validates HTTP status codes, JSON responses
- May use mocked services

**Example**:
```python
def test_create_backup_success(client, mock_backup_service):
    response = client.post("/api/v1/admin/backup")
    assert response.status_code == 200
    assert "backup" in response.json()
```

### CLI Tests (`tests/cli/`)

**Purpose**: Test Click commands as users would invoke them.

**Characteristics**:
- Fast execution with mocked HTTP client
- Tests user interaction (prompts, confirmations)
- Validates console output
- Tests command-line argument parsing

**Example**:
```python
def test_restore_success(runner, mock_client):
    result = runner.invoke(admin, ['restore', 'backup.db', '--confirm'], input='y\n')
    assert result.exit_code == 0
    assert "Restore Successful" in result.output
```

## Test Fixtures

### Common Fixtures (conftest.py)

- `test_data_dir`: Path to test data directory
- `mock_api_client`: Mocked HTTP client
- `reset_database_state`: Auto-cleanup between tests

### Backup-Specific Fixtures

- `temp_db`: Temporary SQLite database
- `temp_backup_dir`: Temporary backup directory
- `mock_settings`: Mocked application settings
- `runner`: Click CliRunner for CLI tests
- `client`: FastAPI TestClient for API tests
- `mock_backup_service`: Mocked backup service

## Writing New Tests

### Unit Test Template

```python
import pytest
from src.bcd_api.services import backup_service

class TestNewFeature:
    """Test new backup feature"""

    def test_feature_success(self, temp_db, mock_settings):
        """Test successful operation"""
        result = backup_service.new_feature()
        assert result is not None

    def test_feature_error_handling(self, mock_settings):
        """Test error handling"""
        with pytest.raises(ValueError):
            backup_service.new_feature(invalid_param=True)
```

### API Test Template

```python
def test_new_endpoint(client, mock_backup_service):
    """Test new API endpoint"""
    response = client.post("/api/v1/admin/new-endpoint")
    assert response.status_code == 200
    assert "expected_key" in response.json()
```

### CLI Test Template

```python
def test_new_command(runner, mock_client):
    """Test new CLI command"""
    result = runner.invoke(admin, ['new-command'])
    assert result.exit_code == 0
    assert "expected output" in result.output
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -e ".[dev]"
      - run: pytest --cov=src --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Troubleshooting

### Import Errors

```bash
# Ensure src/ is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
pytest
```

### Slow Tests

```bash
# Run only fast unit tests
pytest tests/unit/ -v

# Skip slow tests
pytest -m "not slow"
```

### Failed Tests

```bash
# Show detailed output for failures
pytest -v --tb=long

# Stop on first failure
pytest -x

# Re-run only failed tests
pytest --lf
```

### Coverage Not Updating

```bash
# Clear pytest cache
pytest --cache-clear

# Remove old coverage data
rm -rf .coverage htmlcov/

# Run tests again
pytest --cov=src
```

## Best Practices

### ✅ DO

- Use descriptive test names (`test_create_backup_success` not `test1`)
- Test both success and failure cases
- Use fixtures for common setup
- Mock external dependencies (API calls, file I/O)
- Keep tests isolated (no shared state)
- Use parametrize for testing multiple inputs
- Add docstrings to test classes and complex tests

### ❌ DON'T

- Test implementation details (test behavior, not internals)
- Use real databases (use temp files or mocks)
- Make tests depend on execution order
- Use sleep() for timing (use mocks or explicit time control)
- Skip cleanup (use fixtures with yield)
- Write tests without assertions

## Test Metrics

### Performance Targets

- Unit tests: <1ms per test
- Integration tests: <100ms per test
- Full test suite: <5 seconds

### Coverage Targets

- Critical code (backup/restore): 100%
- Services: 90%+
- API endpoints: 90%+
- CLI commands: 80%+
- Overall project: 80%+

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Click Testing](https://click.palletsprojects.com/en/8.1.x/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
