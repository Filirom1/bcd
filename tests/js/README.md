# Fast JavaScript tests

This suite tests Web UI logic **without starting FastAPI or Chromium**. It complements the Playwright suite: HTTP-contract, reactive-state, local-persistence, and component regressions should fail here before E2E tests are run.

## Commands

```bash
# Nix provides Node.js in the development shell
npm ci

# Fast feedback
npm run test:js

# Separate JS report
npm run test:js:coverage

# Development mode
npm run test:js:watch

# Run one domain or one test file
npm run test:js -- tests/js/components/circulation
npm run test:js -- tests/js/pages/circulation/CirculationPage.test.js

# Python coverage, separate from JavaScript coverage
pytest tests -m "not external and not e2e and not slow" \
  --cov=src --cov-report=term-missing --cov-report=html --cov-report=xml
```

The reports must not be added together: they cover different languages and runtimes.

| Scope | CI command | Artifacts |
|---|---|---|
| Python | `pytest … --cov=src` | `coverage.xml`, `htmlcov/` |
| JavaScript | `npm run test:js:coverage` | `coverage-js/lcov.info`, `coverage-js/index.html` |
| Browser journeys | `pytest tests/e2e -m e2e` | Playwright failure screenshots |

## Layout

The layout mirrors `src/bcd_web_vue/js/` so a source module and its tests can be
found from the same domain name.

```text
tests/js/
├── api/                     # REST transport contracts
├── components/
│   └── <domain>/             # Component contracts by source domain
├── composables/              # Vue state, filters, persistence, lifecycle
├── fixtures/                 # Plain domain-object factories; no mocks or DOM
├── helpers/                  # Shared transport responses, stubs, and i18n control
├── models/                   # Errors and DOM-free models
├── pages/
│   └── <domain>/             # Shallow-mounted page workflows
├── setup/
│   └── globals.js            # Vendored Vue/VueRouter/VueI18n test adaptation
├── utils/                    # Pure utility functions
└── README.md
```

Create a domain directory only when its first test is added. Do not create an
alternative `unit/`, `spec/`, `__tests__/`, or source-adjacent test tree.

The application is built for production using Vite (via `npm run build:web`). Vitest, JSDOM, Vue, and Vue Test Utils are development-only dependencies.
The test Vue version is deliberately aligned with the npm package version used in the production build.

## Test placement and naming

| Source type | Test location | Example |
|---|---|---|
| API client | `api/` | `api/client.test.js` |
| Pure composable | `composables/` | `composables/useSelection.test.js` |
| Domain component | `components/<domain>/` | `components/circulation/BorrowerScanner.test.js` |
| Page workflow | `pages/<domain>/` | `pages/circulation/CirculationPage.test.js` |
| Pure model or utility | `models/` or `utils/` | `models/error.test.js` |

Use the source filename followed by `.test.js`. A test file should cover one public
component, composable, model, utility, or API client contract.

## Shared test support

### Fixtures

`fixtures/` contains small factories for domain data. Factories must return fresh
plain objects and accept overrides:

```js
const borrower = makeBorrower({ borrower_id: 'B-204', active: false });
```

Do not put fetch mocks, Vue wrappers, or assertions in fixtures.

### Helpers

- `helpers/http.js`: create transport-boundary `Response` objects.
- `helpers/i18n.js`: set a controlled translation function for a component test.
- `helpers/stubs.js`: minimal child-component doubles for parent contracts.

A helper should represent a stable test contract used by more than one test. Keep a
single-use helper local to its test file until a second use appears.

### Setup

`setup/globals.js` adapts the browser globals used by the vendored application. It
also resets the translation function and DOM after every test. Do not add feature
fixtures, API responses, or application state to this global setup.

## Test boundaries

### API tests

Test URLs, request options, headers, serialization, response parsing, loading state,
and error normalization. Mock `fetch` only here.

### Component and page tests

Mock the API client or child component boundary, then assert a user-visible contract:

- emitted command or event;
- request payload;
- local state update;
- rendered state;
- translated notification or validation error.

Shallow-mount large pages and stub visual children. Mount a real child only when the
parent/child interaction is the contract being tested.

### E2E tests

Keep E2E tests for browser-only or integration-only behavior: keyboard focus,
scanner input, downloads/uploads, routing, printing, charts, static resources,
accessibility, and persisted server mutations.

When a fast JS test supersedes a redundant E2E state permutation, follow the
non-destructive process in [`../e2e/README.md`](../e2e/README.md): mark the E2E test
`e2e_to_be_removed`, keep it running, and remove it only in a dedicated review.

## Coverage policy

Vitest measures first-party Web UI source and publishes a separate report. The report
is the source of truth for current measurements. Each extracted pure-logic module
must receive nominal, boundary, and error tests. Introduce a progressive JS threshold
only after the relevant domain has a stable baseline; never combine it with the
Python threshold.
