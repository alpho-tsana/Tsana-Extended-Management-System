# Changelog

All notable changes to TEMS (Tsana Extended Management System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.6] - 2026-02-19

### Added
- **Mod conflict detection** (`tems.py conflicts`) - Scans installed mods for duplicate PBO filenames, duplicate `.bikey` key files, and duplicate entries in LGSM config; TUI screen via `[c]`
- **Dependency checker** (`tems.py deps`) - Parses `requiredAddons[]` from each mod's `mod.cpp` and reports which dependencies are missing from the installed mod set; TUI screen via `[d]`
- **Backup restore** (`tems.py restore`) - Lists available `.tar.gz` backups, lets you pick one and choose a restore destination (defaults to `backup_dir/restore/`); TUI screen via `[r]` with a selectable DataTable
- **Server monitor** (`tems.py monitor`) - Shows DayZ server process status, RAM usage, CPU load averages, disk usage for server/mods/backup dirs, mod count and system uptime; TUI screen via `[m]` with F5/r refresh

### Changed
- **Menu expanded** - CLI menu grows from 9 to 13 options; TUI adds `r/c/d/m` keybindings alongside existing `1–8`
- **Version bump** - `TEMS_VERSION` → `0.6`

---

## [0.5] - 2026-02-17

### Changed
- **TUI redesigned** - Main menu screen now uses TIPH-style dashboard layout:
  - Left panel: live server status (mod count, mods dir size, active mission, Steam user)
  - Right panel: numbered menu buttons with descriptions
  - Bottom: scrolling event log with timestamps
- **Inline CSS** - TUI stylesheet merged into `tems_tui.py`; `tems_tui.tcss` no longer required
- **TSANA FORGE aesthetic** - Dark navy (`#1a1a2e`) background, orange (`#ff8c00`) accent throughout
- **Event log** - Tracks navigation between screens (entry and return) with timestamps
- **Status refresh** - Status panel auto-updates when returning from any operation screen

### Removed
- `tems_tui.tcss` - Stylesheet now embedded in `tems_tui.py`

---

## [0.4] - 2026-02-14

### Added
- **TIPH integration** - TIPH (Tsana Internet Protocol Helper) added as companion tool
- **TIPH TUI** - Full settings management via TUI: add/remove/manage webhooks, interval settings

---

## [0.3] - 2026-02-08

### Added
- **Textual TUI** - Full graphical terminal user interface via `tems_tui.py`
- **Dedicated TUI screens** - Individual screens for all operations
- **Real-time log output** - Worker-threaded operations stream to RichLog widgets
- **Modal confirmation dialogs** - Yes/No modals with keyboard shortcuts (y/n/Escape)
- **Keyboard navigation** - Number keys, Escape to go back, q to quit
- **Mouse support** - Clickable menus, buttons, inputs
- **Progress indicators** - Visual progress bars for long operations
- **Custom TCSS stylesheet** - `tems_tui.tcss` for TUI theming
- **Dual interface** - TUI and CLI share the same backend

---

## [0.2] - 2026-02-07

### Added
- **XML Merge** - DMXM tool integrated as menu option 8
- **XML merge submenu** - Quick merge, merge specific, list mods, switch mission, auto-detect, manage missions, merge settings
- **XML backup system** - Automatic backups before each merge
- **Multi-mission support** - Configure and switch between multiple missions
- **merge_config.json** - Auto-generated XML merge config

### Changed
- **Menu loops** - Returns after every action instead of exiting
- **Graceful error handling** - Errors return to menu instead of crashing

---

## [0.1] - 2026-02-06

### Added
- **Initial TEMS release** - Forked and rebranded from DSEMS v0.6
- **Consolidated Python tool** - Single `tems.py` replaces all shell scripts
- **ASCII art banner** - TEMS logo on startup
- **CLI subcommands** - `install`, `batch-install`, `update`, `reorder`, `export`, `cleanup`, `backup`
- **Interactive menu** - Guided operation without arguments
- **YAML configuration** - `tems.yaml` for all settings
- **Batch SteamCMD sessions** - Multiple mods in one session
- **Online Workshop validation** - ID checking before download
- **Automatic Workshop cleanup** - Removes downloads after copying
- **Backup command** - Interactive menu, scopes, local/rclone destinations
- **Backup rotation** - Configurable retention
- **Cron-compatible** - `--yes` flag for scheduled operations
- **`--config` flag** - Custom config path for multi-server setups

---

## Roadmap

### Planned for 1.0
- [ ] Web-based dashboard (optional)
- [ ] Complete test coverage
- [ ] Distribution via package managers

---

[0.6]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.6
[0.5]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.5
[0.4]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.4
[0.3]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.3
[0.2]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.2
[0.1]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.1
