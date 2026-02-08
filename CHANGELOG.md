# Changelog

All notable changes to TEMS (Tsana Extended Management System) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Planned for 0.2
- [ ] Mod conflict detection
- [ ] Dependency checker
- [ ] Backup restore command

### Planned for 0.3
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

**Reporting Bugs:** Please include TEMS version in issue reports.

**Feature Requests:** Suggestions welcome! Open an issue with the "enhancement" label.

---

[0.1]: https://github.com/EngineerAlpho/TsanaExtendedManagementSystem/releases/tag/v0.1
