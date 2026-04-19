# BCD Kids - Godot Client – Technical Documentation

Simplified Godot client for children aged 6–11 for the BCD library
system.

## Development Setup

1. Open the project in **Godot 4.6+**
2. Launch `main.tscn`
3. The BCD API must be running on `localhost:8000`

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
1. Searches for BCD servers on the local network via mDNS
2. Lists found servers with their library name
3. Allows the user to select a server

**Prerequisite**: the BCD server must have `library_code` set in its
configuration to be discoverable.

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
