# TODO — External catalog source timeouts

- [x] Inspect the existing per-source timeout settings and compare the current flow with `v2`.
- [x] Lower the default per-request timeouts for BnF, Google Books, and SUDOC.
- [x] Migrate existing installations from old defaults without overwriting customized values.
- [x] Update the settings UI help and verify all provider calls use the configured timeout.
- [x] Add/update focused backend and frontend tests, including migration coverage.
- [x] Run focused backend and frontend tests, Ruff, Black, and migration-head validation.
