# Godot tests

The Godot tests are headless `SceneTree` scripts. They use direct assertions and
exit with status `0` on success or `1` on failure. They do not require a running
BCD server.

## Run the suite

From the repository root:

```bash
# Direct runner
python scripts/run_godot_tests.py

# Unified runner
python run_tests.py godot
npm run test:godot
npm run test:godot:coverage

# Run one script while developing it
python scripts/run_godot_tests.py \
  --test bcd_kids/tests/components_test.gd
```

The runner imports the project before testing so `class_name` scripts work from
a clean checkout. It uses temporary `HOME`/`XDG_*` directories and sets
`BCD_GODOT_TESTS=1` to prevent the normal startup server-discovery loop. If
Godot is not installed, it skips cleanly; `nix-shell` supplies the project’s
Godot 4.6 executable.

## Coverage

Stock Godot has no source-line coverage API. The optional runner instruments a
temporary project copy and reports **function-entry coverage**:

```bash
python scripts/run_godot_tests.py --coverage
python scripts/run_godot_tests.py --coverage --coverage-threshold 80
# or as part of all suites:
python run_tests.py all --cov
```

Reports are written to the ignored `coverage-godot/` directory:

- `coverage.json` — machine-readable report
- `coverage.txt` — summary and missing functions
- `coverage.lcov` — LCOV-compatible function records
- `coverage.html` — browsable summary

The discovery parser is covered with synthetic DNS-SD packets and the discovery
screen is tested offline; neither suite requires multicast or a running server.
This report is separate from Python and JavaScript coverage.

A separate live integration test starts a real Python zeroconf advertiser and
then checks the standalone/native Godot path (without the Python CLIENT_ONLY
proxy), as well as the proxy path:

```bash
pytest tests/integration/test_mdns_live.py -m external -v --no-cov
```

It is intentionally not part of the deterministic Godot runner because it
requires a multicast-capable IPv4 interface and a local Godot executable.

## Test files

| File | Scope |
|---|---|
| `api_contract_test.gd` | API helpers, autoload delegation, i18n fallback |
| `core_test.gd` | State, settings, themes, badges, API error contracts |
| `components_test.gd` | Component scenes, visual states, and signals |
| `screens_test.gd` | Screen scene contracts and rendered states |
| `behavior_test.gd` | Navigation, keyboard/input, fallback and action paths |
| `mdns_test.gd` | DNS-SD query encoding, packet parsing, validation, and peer building |
| `server_discovery_test.gd` | Offline discovery-screen helpers, cards, auth, and splash states |

## Writing tests

- Name new files `*_test.gd` so the runner discovers them.
- Extend `SceneTree` and start the test body with `call_deferred("_run")`.
- Use `tests/test_support.gd` for assertions and `await wait_frames(...)`.
- Instantiate real `.tscn` scenes and attach them with `get_root().add_child(...)`.
- Wait one frame after adding/removing nodes because `@onready` setup and
  `queue_free()` are deferred.
- Keep the normal Godot tests deterministic: do not use a real server or
  multicast discovery. The explicit live mDNS check is in
  `tests/integration/test_mdns_live.py` instead.
- Restore global `GS`, `Settings`, and theme state before finishing.
