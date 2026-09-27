# BCD Kids - Godot Client – Technical Documentation

Simplified Godot client for children aged 6–11 for the BCD library
system.

## Development Setup

1. Open the project in **Godot 4.6+**
2. Launch `main.tscn`
3. The BCD API must be running on the local network (or on `localhost:8888` for local development)

## Testing the Godot Client

The Kids client has a deterministic headless test suite. Tests do not require a
running BCD server: response and successful-workflow tests use an in-process
loopback HTTP fixture, while component and screen tests instantiate the real
`.tscn` scenes.

### Prerequisites

The recommended Nix development shell provides the matching Godot executable:

```bash
nix-shell
command -v godot       # Godot 4.6.3 (or a compatible 4.6+ release)
```

Without Nix, install Godot 4.6+ and make `godot` or `godot4` available on
`PATH`. You can select another executable explicitly with `GODOT_BIN`.

### Running tests

From the repository root:

```bash
# Godot tests only
python scripts/run_godot_tests.py
python run_tests.py godot
npm run test:godot
npm run test:godot:coverage

# Run one test script while developing it
python scripts/run_godot_tests.py \
  --test bcd_kids/tests/components_test.gd

# Run all project suites (Python, JavaScript, Godot)
python run_tests.py all --fast
```

The runner imports the project in a clean headless editor process before
running tests. It uses temporary `HOME`/`XDG_*` directories, so test settings do
not overwrite a developer's Godot profile or `bcd_settings.cfg`. If Godot is
not installed, the direct runner skips cleanly; CI installs Godot and executes
the suite.

### Writing a test

Test scripts live in `bcd_kids/tests/` and follow the `*_test.gd` naming
convention. A test is a headless `SceneTree` script with a deferred entry point:

```gdscript
extends SceneTree

const SUPPORT = preload("res://tests/test_support.gd")
var test := SUPPORT.new()

func _init() -> void:
    call_deferred("_run")

func _run() -> void:
    await test.wait_frames(self, 2)
    test.expect(load("res://src/components/BookCard.tscn") != null,
        "BookCard scene loads")
    test.finish(self)
```

Use the shared helpers in `tests/test_support.gd` for assertions and frame
synchronization. For scene tests, instantiate the production scene, add it to
`get_root()`, wait at least one frame for `@onready` fields and queued frees,
then exercise its public signals or methods:

```gdscript
var card = load("res://src/components/BookCard.tscn").instantiate()
get_root().add_child(card)
await test.wait_frames(self)
card.setup({"title": "A book", "available_copies": 1}, "Reserve", Color.WHITE)
test.equal(card.get_node("Content/TitleLabel").text, "A book",
    "BookCard displays the title")
card.queue_free()
await test.wait_frames(self)
```

Keep the normal Godot tests deterministic:

- Do not call a real school server or depend on multicast/mDNS from the normal
  Godot test runner.
- Use the real `.tscn` files rather than rebuilding UI nodes in the test.
- Mock network outcomes through the empty `GS.base_url` path or the in-process
  `api_test_server.gd` fixture; never depend on a real school server.
- Clean up nodes and restore global `GS`, `Settings`, and theme state.
- Keep user-facing strings in locale files; test translation keys in both `fr`
  and `en` where relevant.
- Test mDNS parsing with synthetic DNS-SD packets in the deterministic suite.
  The separate live test `tests/integration/test_mdns_live.py` starts a real
  zeroconf advertiser and checks both the Python CLIENT_ONLY proxy and the
  standalone/native Godot client.

Current suites:

| Test file | Scope |
|---|---|
| `api_contract_test.gd` | API helpers, autoload delegation, i18n fallback |
| `core_test.gd` | Global state, settings, themes, badges, API error contracts |
| `components_test.gd` | Reusable component scenes, display states, and signals |
| `screens_test.gd` | Screen scene contracts and rendered empty/populated states |
| `behavior_test.gd` | Navigation, keyboard/empty input, fallback and action paths |
| `mdns_test.gd` | DNS-SD query encoding, packet parsing, validation, and peer building |
| `server_discovery_test.gd` | Offline discovery helpers, cards, authentication, and splash states |
| `api_transport_test.gd` | Real HTTP response matrix, auth headers, digest retry, methods, and bodies |
| `workflows_test.gd` | Successful checkout/return/search/hold/name/class and main-menu workflows |
| `discovery_branches_test.gd` | Proxy/health response branches, connection auth, and peer merging |
| `settings_branches_test.gd` | Corrupt/partial persistence, all display controls, theme preview/apply/back |
| `component_branches_test.gd` | Focus styles, cover decode fallbacks, and repeated setup signals |
| `main_behavior_test.gd` | Quit-dialog labels, close guard, confirmation wiring, and cancellation |

### Godot function coverage

Stock Godot does not provide source-line coverage. The project therefore offers
an explicit, dependency-free **function-entry coverage** mode. It instruments a
temporary copy of the project, records which production functions are entered,
and never modifies the working tree:

```bash
python scripts/run_godot_tests.py --coverage
python scripts/run_godot_tests.py --coverage --coverage-threshold 80
python run_tests.py all --cov
```

Reports are written to the ignored `coverage-godot/` directory:

- `coverage.json` — machine-readable report
- `coverage.txt` — terminal-friendly summary with missing functions
- `coverage.lcov` — LCOV-compatible function records
- `coverage.html` — browsable report

This is function coverage, not line or branch coverage. It is intentionally
separate from Python `coverage.py` and JavaScript Vitest coverage. Discovery
parsing and screen helpers are included in the denominator and tested without
multicast. Use the report to find untested screens and behaviors rather than
treating it as a claim that every line is covered.

## Architecture

### Autoloads (Singletons)

| File | Role |
|---|---|
| `GS.gd` | Global state (current user, books, settings) |
| `API.gd` | HTTP client for the BCD REST API |
| `I18n.gd` | FR/EN translation system with runtime switching |
| `Mgr.gd` | Screen manager + notification system |

### Reusable Components

| Component | Description |
|---|---|
| `AutocompleteInput` | Text field with suggestions + barcode scanner detection |
| `FilterPanel` | Dynamic filter panel (Type, Genre, Category, Audience) |
| `BookCard` | Book card widget with status and action buttons |

### Screens

| # | Scene | Description |
|---|---|---|
| 0 | `SServerDiscovery` | mDNS server discovery + manual connection fallback |
| 1 | `SClassSelect` | Class selection |
| 2 | `SNameInput` | First name input with search |
| 3 | `SMainMenu` | Main menu hub |
| 4 | `SCheckout` | Borrow by barcode scan |
| 5 | `SReturnScan` | Return by barcode scan |
| 6 | `SSearch` | Advanced search with dynamic filters |
| 7 | `SHoldConfirm` | Reservation confirmation |
| 8 | `SMyHolds` | Reservation management |

## Server Discovery (mDNS)

The client starts with a discovery screen that:
1. Queries `_bcd._tcp.local.` directly with the Godot `PacketPeerUDP` API
2. Parses DNS-SD PTR, SRV, TXT and IPv4 A records
3. Builds HTTP URLs from the returned IPv4 address and port
4. Lists found servers with their library name
5. Allows the user to select a server

Discovery does not depend on resolving the advertised `.local` hostname through
Avahi/NSS. This is important on school machines where `avahi-browse` can see a
service but applications cannot resolve `*.local`.

When BCD is launched in `CLIENT_ONLY` mode with the Kids client, the Python
launcher runs an optional loopback proxy that uses the existing `zeroconf`
implementation. It does not start the normal BCD API or the database; it
only exposes the existing peer snapshot endpoint to Kids. If Kids is launched directly without the Python
launcher, it uses its native `PacketPeerUDP` implementation instead. Python and
Avahi are therefore not mandatory client dependencies.

The BCD server must have `library_code` set in its configuration to be
advertised. The client also probes `127.0.0.1` and `::1` so a server bound only
to loopback still works when mDNS is disabled. Manual URL entry remains
available as a final fallback.

The direct implementation currently targets IPv4 because the BCD server
advertises IPv4 addresses.

The 🌐 button on `SClassSelect` returns to `SServerDiscovery` at any time.

## Settings Storage

User settings (resolution, quality) are persisted to:

```
user://bcd_settings.cfg
```

They are automatically restored on next startup.

## Barcode Handling

Barcode prefixes are automatically stripped before API calls:

| Prefix | Type |
|---|---|
| `.` | Library items (books) |
| `%` | Borrowers |

## System Requirements

### Minimum (school PCs)

| Component | Requirement |
|---|---|
| CPU | Intel Core 2 Duo / AMD equivalent (≥ 2 GHz) |
| RAM | 4 GB (app uses ~200–300 MB) |
| GPU | Intel HD Graphics 2000 or better (OpenGL 3.3+) |
| Storage | 100 MB free, HDD compatible |
| OS | Windows 10 64-bit or Linux 64-bit |
| Network | Local network for mDNS and API |

### Recommended

| Component | Requirement |
|---|---|
| CPU | Intel Core i3 or better |
| RAM | 8 GB |
| GPU | Dedicated GPU, OpenGL 4.x |
| Storage | SSD |

## Performance Optimizations

Targeting **old school hardware**:

### Rendering
- ✅ OpenGL Compatibility renderer — broad hardware support
- ✅ VSync enabled — caps at 60 FPS, reduces CPU load
- ✅ Anti-aliasing disabled — reduces GPU load
- ✅ Lightweight texture compression
- ✅ Message queue capped at 4 MB

### Antivirus Compatibility
- ✅ Console wrapper disabled — avoids false positives
- ✅ Full Windows product metadata embedded
- ✅ No code obfuscation
- ✅ Open source — fully auditable

### Startup
- ✅ Cold start < 5 seconds on HDD
- ✅ Memory footprint ~200 MB at idle
- ✅ No external runtime dependencies

## UI Design Constraints

Defined for the target audience (ages 6–11):

- Bright color palette
- Button height ≥ 60 px
- Font size ≥ 14 pt
- Animations for feedback (pop-in, flash, shake)
- No sounds (library environment)
- Adjustable graphic quality (pixelated low / smoothed high)
