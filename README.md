# TEMS - Tsana Extended Management System

**Version 0.6** | **Professional mod management for DayZ Linux servers using SteamCMD and LinuxGSM**

Created by alpho-tsana (with assistance from Claude/Anthropic) | License: GPL-3.0

[![Version](https://img.shields.io/badge/version-0.6-orange.svg)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-GPL--3.0-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-yellow.svg)](https://www.python.org/)

---

## Overview

A single, consolidated Python tool for managing DayZ server mods on Linux. From downloading and installing mods to updating, reordering, XML merging, backup, and server diagnostics — TEMS handles it all from one unified interface.

TEMS v0.6 adds four new diagnostic and maintenance commands: mod conflict detection, dependency checking, backup restore, and a live server performance monitor.

### Key Features

- **TIPH-style TUI dashboard** — Live server status panel, numbered menu, event log with timestamps
- **CLI + TUI** — Classic CLI (`tems.py`) or graphical TUI (`tems_tui.py`)
- **Automated Workshop Downloads** — Direct Steam Workshop integration via SteamCMD
- **Batch Installation** — Install dozens of mods from a list file in one session
- **One-Command Updates** — Update all mapped mods at once
- **Interactive Load Order Manager** — Reorder mods with j/k keys or mouse
- **Mod XML Merging** — Merge mod types.xml, events.xml, and spawnabletypes.xml
- **Mod List Export** — Backup and share your server setup
- **Server Backup + Restore** — Local disk or cloud (rclone), restore from any saved archive
- **Mod Conflict Detection** — Find duplicate PBOs and key files across mods
- **Dependency Checker** — Verify requiredAddons from mod.cpp against installed mods
- **Server Monitor** — Real-time process, RAM, CPU load, and disk stats
- **Config Cleanup** — Remove mods from server configuration
- **Inline CSS** — No external `.tcss` file required

### What's New in v0.6

- **Mod conflict detection** (`conflicts`) — Scans all installed mods for duplicate `.pbo` filenames, duplicate `.bikey` key files, and duplicate entries in LGSM config
- **Dependency checker** (`deps`) — Parses `requiredAddons[]` from each mod's `mod.cpp` and flags anything missing from your install
- **Backup restore** (`restore`) — Lists available `.tar.gz` backups with sizes and timestamps; pick one and restore to a safe location or custom path
- **Server monitor** (`monitor`) — Live view of DayZ server process status, RAM usage, CPU load averages (1/5/15 min), per-directory disk usage, mod count, and system uptime; TUI has F5/r refresh

---

## Quick Start

### 1. Install dependencies

```bash
pip install textual requests --break-system-packages
```

### 2. Configure

```bash
nano tems.yaml
# Set steam_user and steam_pass
# Adjust paths if needed (defaults work for standard LinuxGSM setup)
```

### 3. Run

```bash
# TUI mode (recommended)
python3 tems_tui.py

# Classic CLI
python3 tems.py

# CLI subcommands
python3 tems.py install
python3 tems.py batch-install my_mod_list.txt
python3 tems.py update
python3 tems.py reorder
python3 tems.py export
python3 tems.py cleanup
python3 tems.py backup
python3 tems.py restore
python3 tems.py xml-merge
python3 tems.py conflicts
python3 tems.py deps
python3 tems.py monitor
```

---

## TUI Layout (v0.6)

```
┌─ ◈ SERVER STATUS ──┐ ┌─ ◈ MAIN MENU ──────────────────────────────────────┐
│ TEMS ASCII LOGO     │ │ [1]  Install       — Download & install a mod       │
│ v0.6                │ │ [2]  Batch Install — Install from a list file       │
│ ─────────────────   │ │ [3]  Update        — Update all installed mods      │
│ Mods Installed      │ │ [4]  Reorder       — Change mod load order          │
│ 36                  │ │ [5]  Export        — Export mod list to file        │
│ Mods Dir Size       │ │ [6]  Cleanup       — Remove mods from config        │
│ 22.1 GB             │ │ [7]  Backup        — Back up server data            │
│ Active Mission      │ │ [8]  XML Merge     — Merge mod XMLs                 │
│ empty.banov         │ │ [r]  Restore       — Restore from a backup archive  │
│ ─────────────────   │ │ [c]  Conflicts     — Detect conflicting mod files   │
│ Steam User          │ │ [d]  Deps          — Check mod dependencies         │
│ hasq2026            │ │ [m]  Monitor       — View server performance stats  │
└─────────────────────┘ │ [q]  Exit          — Quit TEMS                      │
                        └────────────────────────────────────────────────────┘
┌─ ◈ EVENT LOG ──────────────────────────────────────────────────────────────┐
│ 19:42:11  TEMS v0.6 started. Ready.                                        │
│ 19:42:18  → Opening Monitor...                                             │
│ 19:43:02  ← Returned from Monitor.                                         │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Interfaces

### TUI Mode

```bash
python3 tems_tui.py
```

- Status panel auto-populates from `tems.yaml` and your mod mapping file
- Press `1`–`8`, `r`, `c`, `d`, `m`, or `q` to navigate; all keys shown in the menu panel
- `q` quits from the main menu; `Escape` returns from any sub-screen
- `Escape` returns to the previous screen
- Event log tracks all navigation with timestamps

### CLI Mode

```bash
python3 tems.py
```

Interactive numbered menu. Loops back after each action.

### Subcommands

| Command | Description |
|---------|-------------|
| `install` | Install a single mod (workshop or manual) |
| `batch-install` | Install multiple mods from a list file |
| `update` | Update all installed/mapped mods |
| `reorder` | Interactive load order manager |
| `export` | Export mod list to shareable file |
| `cleanup` | Remove mods from server config |
| `backup` | Back up server data (local/cloud) |
| `restore` | Restore from a backup archive |
| `xml-merge` | Merge mod XML files into mission |
| `conflicts` | Detect duplicate PBOs and key files across mods |
| `deps` | Check mod.cpp requiredAddons against installed mods |
| `monitor` | Show server process, RAM, CPU load, and disk stats |

### Global Options

| Flag | Description |
|------|-------------|
| `--config, -c` | Path to custom `tems.yaml` |
| `--yes, -y` | Skip confirmations (for cron) |

---

## Project Structure

```
tems-0.6/
├── tems.py            # Core CLI + all backend logic
├── tems_tui.py        # Textual TUI frontend (CSS embedded)
├── tems.yaml          # Configuration file
├── merge_config.json  # XML merge config (auto-generated)
├── README.md
├── CHANGELOG.md
├── CONFIGURATION.md
├── INSTALLATION.md
└── TROUBLESHOOTING.md
```

> Note: `tems_tui.tcss` is no longer needed from v0.5 onward.

---

## System Requirements

- Linux server (tested on Ubuntu 24)
- Python 3.10+
- LinuxGSM DayZ server installation
- SteamCMD
- Steam account (doesn't need to own DayZ)
- `pip install textual requests` for TUI

---

## License

GNU General Public License v3.0 (GPL-3.0)

---

## Credits

- **Created by:** alpho-tsana (with assistance from Claude/Anthropic)
- **Special thanks to:** HASQ Gaming Community

**alpho-tsana** | [GitHub](https://github.com/alpho-tsana) | [Discord](https://hasq.net)
