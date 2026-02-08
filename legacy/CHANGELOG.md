# Changelog

All notable changes to DayZ Linux Server Mod Management Scripts will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.6] - 2026-02-04

### Added
- **Centralized Configuration System** - Single config.sh file for all scripts
- **Automatic Workshop Cleanup** - Prevents disk space issues by deleting Workshop files after copying
- **Workshop ID Validation** - Validates Workshop IDs before downloading to catch typos
- **Export Mod List Feature** - Export current setup for backup or cloning servers
- **Comprehensive Documentation** - README, INSTALLATION, CONFIGURATION, and TROUBLESHOOTING guides
- **Version Headers** - All scripts now display version information
- **Multi-server Support** - Config system supports multiple server setups

### Changed
- **Config Management** - Moved from hardcoded paths to config.sh
- **Credential Storage** - Steam credentials now in config.sh instead of each script
- **Path Handling** - All paths now configurable via config.sh
- **Script Headers** - Standardized header format with version, author, license

### Fixed
- **Disk Space Issues** - Workshop downloads no longer accumulate indefinitely
- **Path Errors** - Fixed hardcoded $HOME causing issues when run from different directories
- **Manual Installation** - Improved mod structure validation
- **Workshop Downloads** - Better error handling and retry logic

### Improved
- **Documentation** - Complete rewrite with real-world troubleshooting examples
- **Error Messages** - More helpful error messages with actionable solutions
- **User Experience** - Clearer prompts and progress indicators

---

## [0.5] - 2025-12-XX (Historical)

### Added
- Manual mod installation system
- Mod structure validation
- Multiple key folder location checking

### Changed
- Workshop downloader now offers two methods (Workshop vs Manual)

---

## [0.4] - 2025-11-XX (Historical)

### Added
- Batch installation script
- Example mod list template
- Progress indicators for bulk operations

---

## [0.3] - 2025-10-XX (Historical)

### Added
- Interactive load order manager
- Cleanup utility for mod configuration
- Load order best practices guide

---

## [0.2] - 2025-09-XX (Historical)

### Added
- Automatic mod updater
- Mod mapping file system
- Update all mods functionality

---

## [0.1] - 2025-08-XX (Historical)

### Added
- Initial release
- Workshop mod downloader
- Automatic key management
- Linux case-sensitivity handling
- LinuxGSM config integration

---

## Version Numbering

- **Major (X.0.0)** - Breaking changes, major rewrites
- **Minor (0.X.0)** - New features, significant improvements
- **Patch (0.0.X)** - Bug fixes, minor tweaks

---

## Roadmap

### Planned for 0.7
- [ ] Mod conflict detection
- [ ] Dependency checker
- [ ] Backup/restore system
- [ ] Web-based status dashboard (optional)

### Planned for 0.8
- [ ] Server performance monitoring integration
- [ ] Automated mod testing
- [ ] Rollback functionality

### Planned for 1.0
- [ ] GUI frontend (optional)
- [ ] Complete test coverage
- [ ] Professional packaging
- [ ] Distribution via package managers

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to contribute.

**Reporting Bugs:** Please include script version number in issue reports.

**Feature Requests:** Suggestions welcome! Open an issue with the "enhancement" label.

---

[0.6]: https://github.com/EngineerAlpho/dayz-mod-scripts/releases/tag/v0.6
