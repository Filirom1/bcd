# Barcode Printing - Task List

## Dependency Graph

```
001-infrastructure-setup
 |
 ├──> 002-print-borrower-reference ──┐
 |                                    |
 ├──> 003-print-student-cards      ──┼──> 005-ui-integration
 |                                    |
 └──> 004-print-item-labels        ──┘
```

## Execution Order

| # | Task | Creates | Modifies | Depends On |
|---|------|---------|----------|------------|
| 1 | [Infrastructure Setup](001-infrastructure-setup.md) | `css/print-labels.css` | `index.html`, `router.js`, `App.js`, `en.json`, `fr.json` | None |
| 2 | [Borrower Reference Sheet](002-print-borrower-reference.md) | `pages/PrintBorrowerReference.js` | None | Task 1 |
| 3 | [Student Library Cards](003-print-student-cards.md) | `pages/PrintStudentCards.js` | None | Task 1 |
| 4 | [Item Labels](004-print-item-labels.md) | `pages/PrintItemLabels.js` | None | Task 1 |
| 5 | [UI Integration](005-ui-integration.md) | None | `AdminDropdown.js`, `BorrowersPage.js`, `CatalogPage.js` | Tasks 2, 3, 4 |

## Parallelism

- Tasks 2, 3, 4 are **independent** and can run in parallel after Task 1
- Task 5 must wait for Tasks 2, 3, 4 to all complete

## Key Decisions

- **No backend changes** - All client-side Vue components using existing API endpoints
- **JsBarcode via CDN** - Consistent with project's no-npm architecture
- **CODE39 barcode format** - Default, can be overridden by system settings
- **Print via `window.print()`** - Proven pattern from Reports page
- **Sidebar hidden on print routes** - Via `route.meta.layout === 'print'` check in App.js

## Source Plan

Full plan with mockups: `.trinity/007-barcode-print/plan`
