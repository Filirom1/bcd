# E2E Testing - World-Class Architecture

**Status**: Foundation Complete | Tests In Progress

---

## Overview

This E2E test suite follows industry best practices with:
- **Function-scoped isolation** - Each test gets fresh database
- **Page Object Model** - Centralized selectors, business methods
- **Test data factories** - Fast, flexible test data creation
- **Performance measurement** - Built-in performance monitoring
- **Screenshot on failure** - Automatic debugging artifacts

---

## Structure

```
tests/e2e/
├── conftest.py                    # Test configuration (isolation, fixtures)
├── page_objects/                  # Page Object Model
│   ├── base_page.py               # Base class with common methods
│   ├── circulation_page.py        # Checkout/return operations
│   ├── catalog_page.py            # Search/browse operations
│   ├── borrowers_page.py          # Borrower management
│   └── settings_page.py           # System settings
├── fixtures/                      # Test data factories
│   ├── borrower_factory.py        # Create test borrowers
│   └── item_factory.py            # Create test items/records
├── helpers/                       # Utilities
│   └── performance.py             # Performance measurement
├── test_us1_circulation.py        # US1 tests (exemplary)
├── test_us2_catalog.py            # TODO
├── test_us3_borrowers.py          # TODO
├── test_us6_settings.py           # TODO
├── test_cross_cutting.py          # TODO
└── test_performance.py            # TODO
```

---

## Running Tests

### Quick Start

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run all user story tests (US1-US6)
pytest tests/e2e/test_us*.py -v

# Run specific user story
pytest tests/e2e/test_us1_circulation.py -v    # Circulation
pytest tests/e2e/test_us2_catalog.py -v        # Catalog Search
pytest tests/e2e/test_us3_borrowers.py -v      # Borrower Management
pytest tests/e2e/test_us4_cataloging.py -v     # Cataloging with ISBN Lookup
pytest tests/e2e/test_us5_reports.py -v        # Reports & Statistics
pytest tests/e2e/test_us6_settings.py -v       # System Settings

# Run with visible browser (debugging)
HEADED=1 pytest tests/e2e/test_us1_circulation.py -v

# Run single test
pytest tests/e2e/test_us1_circulation.py::TestUS1CirculationBasics::test_us1_ac1_borrower_info_displays -v
```

### Advanced Options

```bash
# Enable video recording
VIDEO=1 pytest tests/e2e/ -v

# Run in parallel (faster)
pytest tests/e2e/ -n 4

# Run in random order (test isolation)
pytest tests/e2e/ --random-order
```

---

## Key Features

### 1. Function-Scoped Isolation

**Problem**: Tests contaminating each other via shared database
**Solution**: Each test gets a fresh copy of base database

```python
# Base database created once per session
base_database → test_e2e_base.db (with migrations + SystemSettings)

# Each test gets its own copy
test_database → test_e2e_1234567890.db (copied from base)
```

**Benefits**:
- Tests can run in any order
- Parallel execution possible
- No state leaks between tests
- Faster than full migrations per test

### 2. Page Object Model

**Centralized selectors and business methods**

```python
# Bad (scattered selectors)
page.locator('input[inputmode="numeric"]').fill("101")
page.locator('button:has-text("Rechercher")').click()

# Good (Page Object)
circulation_page.enter_borrower_id("101")
```

**Benefits**:
- Change selector once, updates all tests
- Business-focused test code
- Reusable methods

### 3. Test Data Factories

**On-demand test data creation**

```python
# Create borrower with sensible defaults
borrower = borrower_factory.create(borrower_id="101")

# Create with specific attributes
borrower = borrower_factory.create_blocked(reason="Lost Book")

# Create batch
borrowers = borrower_factory.create_batch(count=10)
```

**Benefits**:
- Fast (no CSV parsing)
- Flexible (exact scenario needed)
- Isolated (each test own data)

### 4. No Flaky Waits

**Problem**: Fixed timeouts fail randomly
**Solution**: Explicit waits for elements

```python
# Bad (flaky)
page.click('button')
page.wait_for_timeout(1000)  # Hope it's done

# Good (reliable)
page.click('button')
page.wait_for_selector('.result', state='visible')  # Polls until visible
```

### 5. Screenshot on Failure

Tests automatically capture screenshots when they fail:

```
test-results/screenshots/test_us1_ac1_borrower_info_displays.png
```

---

## Test Coverage

### User Stories (from spec.md)

| User Story | Tests | Status |
|-----------|-------|--------|
| US1: Circulation | 9 | ✅ Complete (test_us1_circulation.py) |
| US2: Catalog | 8 | ✅ Complete (test_us2_catalog.py) |
| US3: Borrowers | 14 | ✅ Complete (test_us3_borrowers.py) |
| US4: Cataloging | 7 | ✅ Complete (test_us4_cataloging.py) |
| US5: Reports | 5 | ✅ Complete (test_us5_reports.py) |
| US6: Settings | 5 | ✅ Complete (test_us6_settings.py) |

### Cross-Cutting Concerns

| Concern | Tests | Status |
|---------|-------|--------|
| i18n (FR/EN) | 5 | TODO |
| Responsive Design | 4 | TODO |
| Error Handling | 6 | TODO |
| Performance | 5 | TODO |
| Accessibility | 8 | TODO |

**Total**: 46 user story tests (US1-US6)
**Passing**: Run `pytest tests/e2e/ -v` to see current status
**Status**: Foundation complete ✅

> **Note**: Test counts and pass rates should be verified by running the test suite. Numbers may be out of date.

---

## Writing New Tests

### Template

```python
"""
E2E Tests for US#: Feature Name

Tests acceptance scenarios from specs/003-web-ui/spec.md:
- US#-AC1: Scenario description
- US#-AC2: Scenario description
"""

import pytest


class TestFeatureBasics:
    """Basic workflows."""

    def test_us#_ac1_scenario_name(self, page_object, factory):
        """
        US#-AC1: Scenario description.

        Arrange: Setup test data
        Act: Perform user action
        Assert: Verify expected result
        """
        # Arrange
        test_data = factory.create()

        # Act
        page_object.perform_action()

        # Assert
        result = page_object.get_result()
        assert result == expected_value
```

### Best Practices

1. **Use AAA Pattern**: Arrange-Act-Assert
2. **One assertion per test**: Test one thing
3. **Use Page Objects**: Don't access page.locator directly
4. **Use Factories**: Create test data programmatically
5. **Clear naming**: `test_us#_ac#_what_happens`
6. **Add docstrings**: Explain test purpose
7. **No fixed waits**: Use `wait_for_selector()`
8. **Measure performance**: Use `performance_monitor` for critical paths

---

## Debugging

### Test Fails Randomly

**Problem**: Flaky tests
**Diagnosis**: Check for `page.wait_for_timeout()` calls
**Solution**: Replace with `wait_for_selector()`

### Test Fails on CI but Passes Locally

**Problem**: Timing issues
**Diagnosis**: CI slower than local machine
**Solution**: Increase timeouts in selectors

### Can't Find Element

**Problem**: Selector doesn't match
**Diagnosis**: Run with `HEADED=1` to see browser
**Solution**: Update selector in Page Object

### Database State Issues

**Problem**: Test depends on previous test
**Diagnosis**: Run tests in random order `--random-order`
**Solution**: Use factories to create all needed data

---

## Performance Targets

From spec.md:

- **Scanner feedback**: <200ms (p95)
- **Page load**: <3s (cold start)
- **Search results**: <2s
- **Checkout transaction**: <45s
- **Return transaction**: <30s

---

## Maintenance

### Update Selector

1. Find selector in `page_objects/*.py`
2. Update once
3. All tests using that method update automatically

### Add New Page

1. Create `page_objects/new_page.py`
2. Extend `BasePage`
3. Add fixture in `conftest.py`
4. Use in tests

### Add New Factory

1. Create `fixtures/new_factory.py`
2. Add fixture in `conftest.py`
3. Use in tests

---

## Resources

- **Plan**: `/home/nixos/.claude/plans/eager-hopping-sifakis.md`
- **Spec**: `specs/003-web-ui/spec.md`
- **Playwright Docs**: https://playwright.dev/python/
- **Page Object Pattern**: https://martinfowler.com/bliki/PageObject.html

---

## Success Criteria

From the plan:

- [ ] **Reliability**: 99.9% pass rate on CI
- [ ] **Coverage**: 100% of critical paths + 90% of acceptance scenarios
- [ ] **Speed**: Full suite <5 min, critical path <2 min
- [ ] **Maintainability**: Page Object Model, <10% code duplication
- [ ] **Isolation**: Tests pass in any order, parallel execution works

---

**Status**: Foundation complete, ready for test authoring.
