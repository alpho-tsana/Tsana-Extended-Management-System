# TEMS - Tsana Extended Management System

**Version 0.3** | **Professional mod management for DayZ Linux servers using SteamCMD and LinuxGSM**

Created by alpho-tsana (with assistance from Claude/Anthropic) | License: GPL-3.0

[![Version](https://img.shields.io/badge/version-0.3-blue.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-yellow.svg)](https://www.python.org/)

---

## Overview

A single, consolidated Python tool that replaces the original suite of shell scripts for managing DayZ server mods on Linux. From downloading and installing mods to updating, reordering, XML merging, and exporting - TEMS handles it all from one unified interface.

TEMS v0.3 introduces a full **Textual-based TUI** (Terminal User Interface) alongside the original CLI, giving you a modern, interactive graphical experience right in your terminal.

### Key Features

- **Textual TUI** - Rich terminal UI with mouse support, keyboard shortcuts, progress bars, and modal dialogs (`tems_tui.py`)
- **CLI + TUI** - Choose between the classic CLI (`tems.py`) or the new graphical TUI (`tems_tui.py`)
- **Automated Workshop Downloads** - Direct Steam Workshop integration via SteamCMD
- **Manual Installation Support** - Handle mods that fail Workshop downloads
- **Batch Installation** - Install dozens of mods from a list file in one session
- **One-Command Updates** - Update all mapped mods at once
- **Interactive Load Order Manager** - Reorder mods with best-practice guidance (drag-and-drop in TUI)
- **Mod XML Merging** - Merge mod types.xml, events.xml, and spawnabletypes.xml into server mission files
- **Mod List Export** - Backup and share your server setup
- **Server Backup** - Back up world data, mods, and configs to local disk or cloud (via rclone)
- **Config Cleanup** - Remove mods from server configuration
- **Persistent Menu** - Menu loops back after each action; no need to re-launch
- **Linux Compatibility** - Automatic case-sensitivity handling
- **Automatic Workshop Cleanup** - Prevents disk space issues
- **Workshop Validation** - Checks IDs online before downloading

### What's New in v0.3

- **Textual TUI** - Full graphical terminal interface via `tems_tui.py` using the [Textual](https://textual.textualize.io/) framework
  - Dedicated screens for each operation (Install, Batch Install, Update, Reorder, Export, Cleanup, Backup, XML Merge)
  - Real-time log output streamed to rich log widgets
  - Modal confirmation dialogs
  - Keyboard shortcuts (number keys for menu, Escape to go back, q to quit)
  - Mouse-clickable menus, buttons, and interactive forms
  - Progress indicators for long-running operations
  - Custom TCSS stylesheet for consistent theming
- **Dual interface** - Original CLI (`tems.py`) and new TUI (`tems_tui.py`) share the same backend logic

### What Was New in v0.2

- **XML Merge** - The standalone DMXM (DayZ Mod XML Merger) tool fully integrated as menu option 8 / `tems.py xml-merge`
- **Menu loops** - The interactive menu returns after every action instead of exiting
- **Graceful error handling** - Errors in commands return to the menu instead of terminating the script

---

## Quick Start

### 1. Configure

```bash
nano tems.yaml
# Set steam_user and steam_pass
# Adjust paths if needed (defaults work for standard LinuxGSM setup)
```

### 2. Run

```bash
# TUI mode (recommended - requires: pip install textual)
python3 tems_tui.py

# Classic CLI - interactive menu (loops back after each action)
python3 tems.py

# CLI subcommands (direct, non-interactive)
python3 tems.py install
python3 tems.py batch-install my_mod_list.txt
python3 tems.py update
python3 tems.py reorder
python3 tems.py export
python3 tems.py cleanup
python3 tems.py backup
python3 tems.py xml-merge
```

### 3. Done

The tool handles everything: downloading, installing, key management, case conversion, XML merging, and config updates.

---

## Interfaces

### TUI Mode (New in v0.3)

```bash
python3 tems_tui.py
```

Launches a full terminal user interface built with [Textual](https://textual.textualize.io/). Features include:

- **Main menu** with clickable list items and number-key shortcuts
- **Dedicated screens** for each operation with forms, inputs, and real-time log output
- **Modal dialogs** for confirmations (Yes/No with keyboard shortcuts)
- **Escape** returns to the previous screen; **q** quits the application
- **Mouse and keyboard** navigation throughout

Requires the `textual` package:
```bash
pip install textual
```

### CLI Mode

```bash
python3 tems.py
```

The original interactive menu with numbered options. After each command completes, the menu is shown again automatically.

```
  1. Install       - Download & install a single mod
  2. Batch Install - Install multiple mods from a list file
  3. Update        - Update all installed mods
  4. Reorder       - Change mod load order
  5. Export        - Export mod list to file
  6. Cleanup       - Remove mods from config
  7. Backup        - Back up server data
  8. XML Merge     - Merge mod XMLs into mission files
  9. Exit
```

### Subcommands

| Command | Description | Example |
|---------|-------------|---------|
| `install` | Install a single mod (workshop or manual) | `tems.py install -w 2415195639 -n @Banov` |
| `batch-install` | Install multiple mods from a list file | `tems.py batch-install mod_list.txt` |
| `update` | Update all installed/mapped mods | `tems.py update` |
| `reorder` | Interactive load order manager | `tems.py reorder` |
| `export` | Export mod list to shareable file | `tems.py export -o my_mods.txt` |
| `cleanup` | Remove mods from server config | `tems.py cleanup` |
| `backup` | Back up server data (local/cloud) | `tems.py backup -s world,configs -d local` |
| `xml-merge` | Merge mod XML files into mission | `tems.py xml-merge` |

### Global Options (CLI only)

| Flag | Description |
|------|-------------|
| `--config, -c` | Path to custom `tems.yaml` config file |
| `--yes, -y` | Skip confirmation prompts (install, batch-install, update) |

---

## Common Workflows

### Installing a Single Mod

```bash
# TUI - launch and select "Install" from the menu
python3 tems_tui.py

# CLI - Interactive (prompts for workshop ID and name)
python3 tems.py install

# CLI - Non-interactive
python3 tems.py install --workshop-id 2415195639 --name @Banov

# CLI - Manual installation (mod already uploaded to mods dir)
python3 tems.py install --manual
```

### Installing Multiple Mods

```bash
# Create or use a mod list file
python3 tems.py batch-install my_mod_list.txt
```

Mod list format:
```
# Lines starting with # are ignored
DabsFramework - https://steamcommunity.com/sharedfiles/filedetails/?id=2545327648
Banov - https://steamcommunity.com/sharedfiles/filedetails/?id=2415195639
DayZ-Expansion-Core - https://steamcommunity.com/sharedfiles/filedetails/?id=2116151222
```

### Updating All Mods

```bash
python3 tems.py update
```

### Fixing Load Order

```bash
python3 tems.py reorder
```

Best practice order:
1. Map mods (`@Banov`, etc.) first
2. Framework mods (`@CF`, `@DabsFramework`) early
3. `@DayZ-Expansion-Core` before other Expansion mods
4. Dependency mods before mods that require them

### Merging Mod XMLs

After installing mods, many include their own `types.xml`, `events.xml`, or `spawnabletypes.xml` files that need to be merged into your server's mission folder.

```bash
# Interactive - submenu with full merge options
python3 tems.py xml-merge

# Or use option 8 from the main menu (CLI or TUI)
```

The XML Merge submenu provides:
1. **Quick merge** - Auto-scan all mods and merge everything at once
2. **Merge specific** - Merge a single mod folder
3. **List mods** - See which mods have mergeable XML files
4. **Switch mission** - Change which mission folder to merge into
5. **Auto-detect** - Scan for new mission folders
6. **Manage missions** - Add, remove, or edit mission configurations
7. **Merge settings** - Toggle overwrite behavior and backups

XML backups are created automatically before each merge operation.

### Backing Up Your Server

```bash
# Interactive - choose what to back up and where
python3 tems.py backup

# Back up world data and configs to local disk
python3 tems.py backup --scope world,configs --dest local

# Back up everything to local disk and cloud
python3 tems.py backup --scope world,mods,configs --dest local,rclone

# Full server backup via LinuxGSM
python3 tems.py backup --scope full

# Automated (cron-compatible) using config defaults
python3 tems.py backup --yes
```

### Exporting Mod List

```bash
python3 tems.py export -o my_server_backup.txt
```

The exported file can be used with `batch-install` to recreate the setup on another server.

---

## Documentation

- **[Installation Guide](INSTALLATION.md)** - Prerequisites, setup instructions, and TUI installation
- **[Configuration Guide](CONFIGURATION.md)** - `tems.yaml` and `merge_config.json` settings reference
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Common issues and solutions
- **[Changelog](CHANGELOG.md)** - Version history

---

## System Requirements

- Linux server (tested on Ubuntu 24)
- Python 3.10+
- [LinuxGSM](https://linuxgsm.com/) DayZ server installation
- [SteamCMD](https://developer.valvesoftware.com/wiki/SteamCMD) installed
- Steam account (doesn't need to own DayZ)
- **For TUI:** `pip install textual` (optional - CLI works without it)

---

## Configuration

TEMS uses two configuration files:

### tems.yaml (main config)

```yaml
# Steam credentials
steam_user: "your_username"
steam_pass: "your_password"

# Server paths (~ expands to home directory)
server_base_dir: "~"
server_files_dir: "~/serverfiles"
server_mods_dir: "~/serverfiles/mods"
keys_dir: "~/serverfiles/keys"
lgsm_config: "~/lgsm/config-lgsm/dayzserver/dayzserver.cfg"

# SteamCMD
steamcmd_path: "~/.steam/steamcmd/steamcmd.sh"
workshop_dir: "~/.local/share/Steam/steamapps/workshop/content/221100"

# Mod management
mod_mapping_file: "~/.dayz_mod_mapping"
dayz_app_id: 221100

# Backup settings
backup_dir: "~/backups/tems"
backup_rclone_remote: ""
backup_keep: 5
backup_default_scope: ""
backup_default_dest: ""
mission_dir: "~/serverfiles/mpmissions/dayzOffline.chernarusplus"
lgsm_script: "~/dayzserver"
```

### merge_config.json (XML merge config)

Auto-generated on first use of `xml-merge`. Controls mission paths, mod search paths, and merge rules. See [CONFIGURATION.md](CONFIGURATION.md) for details.

---

## Project Structure

```
tems-0.3/
├── tems.py            # Core CLI tool (all backend logic)
├── tems_tui.py        # Textual TUI frontend
├── tems_tui.tcss      # TUI stylesheet
├── tems.yaml          # Configuration file
├── merge_config.json  # XML merge configuration (auto-generated)
├── README.md          # This file
├── CHANGELOG.md       # Version history
├── CONFIGURATION.md   # Configuration reference
├── INSTALLATION.md    # Setup instructions
├── TROUBLESHOOTING.md # Common issues and solutions
└── legacy/            # Original shell scripts (archived)
```

---

## Contributing

Contributions welcome! This is open-source software designed to help the DayZ server admin community.

- Report bugs via issues
- Submit improvements via pull requests
- Share your experience and suggestions

---

## License

GNU General Public License v3.0 (GPL-3.0)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation.

See [LICENSE](LICENSE) for full text.

---

## Credits

- **Created by:** alpho-tsana (with assistance from Claude/Anthropic)
- **Developed for:** DayZ Linux server administration community
- **Special thanks to:** HASQ Gaming Community for testing and feedback

---

## Resources

- [LinuxGSM Documentation](https://linuxgsm.com/)
- [DayZ Official Wiki](https://dayz.com/)
- [Steam Workshop](https://steamcommunity.com/app/221100/workshop/)
- [Textual Framework](https://textual.textualize.io/)

---

**alpho-tsana** | [GitHub](https://github.com/alpho-tsana) | [Discord](https://hasq.net) | [Website](https://alpho-tsana.net)
