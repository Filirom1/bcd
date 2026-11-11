# Catalogue full-text search (SQLite FTS5)

## Baseline (before implementation)

- Commit: `76dfa95`; worktree was clean.
- Local database: `data/bcd.db`, 3,132 bibliographic records.
- `q=adele`, 50 warmed raw-SQL runs; results were the same 42 record IDs:
  - Current accent-folding `LIKE '%...%'`: median 275.551 ms, p95 437.854 ms.
  - Temporary FTS5 trigram `MATCH`: median 9.504 ms, p95 11.890 ms.
  - FTS index build in memory: 394.595 ms.
- Catalogue searchable text contains 38 `œ` and 4 `æ` occurrences (31 and 3 records respectively). The current fold maps these to `oe` and `ae`; preserve that behavior in the new index.
- Measurements are database-query timings, not end-to-end HTTP timings.
- Git baseline versus migrated FTS5 service query (`q=adele`, 25 warmed runs): median 556.252 ms → 23.001 ms (24.18×); p95 707.172 ms → 24.727 ms. Both returned the same 42 record IDs.

## Work checklist

- [x] Identify the general catalogue search path, current matching semantics, and existing accent folding.
- [x] Count ligatures and benchmark current SQL against a temporary FTS5 trigram index before editing tracked code.
- [x] Add a reversible Alembic migration for an FTS5 trigram index and synchronization triggers, including `œ`/`æ` transliteration.
- [x] Replace the SQLite catalogue `q` scan with FTS5 `MATCH`; do not retain a parallel legacy search implementation. Text queries shorter than 3 characters are out of scope.
- [x] Add integration tests for accent-insensitive substrings, ligatures, numeric/ISBN/item-ID search, updates, deletes, and result-count/pagination behavior.
- [x] Add an FTS5 tokenizer-and-accent smoke check to the PyInstaller spec used by Linux and Windows builds.
- [x] Benchmark the changed application query against the Git baseline using the same database and inputs; verify result IDs and record before/after timings.
- [x] Review the final Git diff for scope and migration reversibility.
