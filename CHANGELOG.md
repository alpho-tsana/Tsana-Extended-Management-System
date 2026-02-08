# Changelog

All notable changes to TEMS (Tsana Extended Management System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.3] - 2026-02-08

### Added
- **Textual TUI** - Full graphical terminal user interface via `tems_tui.py` using the [Textual](https://textual.textualize.io/) framework
- **Dedicated TUI screens** - Individual screens for Install, Batch Install, Update, Reorder, Export, Cleanup, Backup, and XML Merge operations
- **Real-time log output** - Worker-threaded operations stream output to rich log widgets in the TUI
- **Modal confirmation dialogs** - Yes/No confirmation modals with keyboard shortcuts (y/n/Escape)
- **Keyboard navigation** - Number keys for menu selection, Escape to go back, q to quit
- **Mouse support** - Full mouse-clickable menus, buttons, inputs, and interactive forms
- **Progress indicators** - Visual progress bars for long-running operations in the TUI
- **Custom TCSS stylesheet** - `tems_tui.tcss` for consistent TUI theming and layout
- **Dual interface architecture** - TUI (`tems_tui.py`) and CLI (`tems.py`) share the same backend logic

---

## [0.2] - 2026-02-07

### Added
- **XML Merge** - Standalone DMXM (DayZ Mod XML Merger) tool fully integrated as menu option 8 / `tems.py xml-merge`
- **XML merge submenu** - Quick merge, merge specific mod, list mods, switch mission, auto-detect missions, manage missions, merge settings
- **XML backup system** - Automatic backups created before each merge operation
- **Multi-mission support** - Configure and switch between multiple mission folders for XML merging
- **Merge rules** - Configurable overwrite behavior, vanilla duplicate skipping, and comment preservation
- **merge_config.json** - Auto-generated configuration file for XML merge settings

### Changed
- **Menu loops** - The interactive menu returns after every action instead of exiting; only "Exit" quits
- **Graceful error handling** - Errors in commands return to the menu instead of terminating the script

---

## [0.1] - 2026-02-06

### Added
- **Initial TEMS release** - Forked and rebranded from DSEMS v0.6 to Tsana Extended Management System
- **Consolidated Python tool** - Single `tems.py` replaces all shell scripts
- **ASCII art banner** - TEMS logo displayed on startup
- **CLI subcommands** - `install`, `batch-install`, `update`, `reorder`, `export`, `cleanup`, `backup`
- **Interactive menu** - Run `tems.py` with no arguments for guided operation
- **YAML configuration** - `tems.yaml` for all settings
- **Batch SteamCMD sessions** - Downloads multiple mods in one session for efficiency
- **Online Workshop validation** - Checks IDs against Steam before downloading
- **Automatic Workshop cleanup** - Removes downloaded files after copying to server
- **Backup command** - `tems.py backup` with interactive menu, scopes, local/rclone destinations
- **Backup rotation** - Automatically remove old archives, keeping a configurable number
- **Cron-compatible automation** - Use `--yes` with config defaults for scheduled operations
- **`--config` flag** - Point to custom config file for multi-server setups
- **Full documentation** - README, Installation, Configuration, and Troubleshooting guides

---

## Roadmap

### Planned for 0.4
- [ ] Mod conflict detection
- [ ] Dependency checker
- [ ] Backup restore command

### Planned for 0.5
- [ ] Server performance monitoring integration
- [ ] Automated mod testing
- [ ] Rollback functionality

### Planned for 1.0
- [ ] Web-based dashboard (optional)
- [ ] Complete test coverage
- [ ] Distribution via package managers

---

## Contributing

See the README for guidelines on how to contribute.

**Reporting Bugs:** Please include TEMS version (shown in banner, currently v0.3) in issue reports.

**Feature Requests:** Suggestions welcome! Open an issue with the "enhancement" label.

---

[0.3]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.3
[0.2]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.2
[0.1]: https://github.com/alpho-tsana/TsanaExtendedManagementSystem/releases/tag/v0.1
