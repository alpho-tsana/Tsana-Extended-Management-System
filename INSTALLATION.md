# Installation Guide

Setup instructions for TEMS - Tsana Extended Management System v0.5.

---

## Prerequisites

- **Linux Server** — Ubuntu 20.04+ or Debian 10+ recommended
- **Python 3.10+** — Check with `python3 --version`
- **LinuxGSM DayZ Server** — [linuxgsm.com](https://linuxgsm.com/servers/dayzserver/)
- **SteamCMD** — Installed automatically with LinuxGSM
- **Steam Account** — Does NOT need to own DayZ
- **rclone** *(optional)* — For cloud backups

---

## Step-by-Step

### 1. Download TEMS

```bash
cd ~
git clone https://github.com/alpho-tsana/TsanaExtendedManagementSystem.git tems
cd tems
```

Or upload `tems.py`, `tems_tui.py`, and `tems.yaml` via SFTP.

### 2. Install dependencies

```bash
pip install textual requests --break-system-packages
```

The CLI (`tems.py`) only needs `requests`. The TUI (`tems_tui.py`) requires both.

### 3. Configure

```bash
nano tems.yaml
```

Required changes:
```yaml
steam_user: "your_steam_username"
steam_pass: "your_steam_password"
```

All other paths default to standard LinuxGSM locations and usually don't need changing.

### 4. Test

```bash
# CLI
python3 tems.py

# TUI
python3 tems_tui.py
```

Press `9` or `q` to exit.

---

## File Layout After Install

```
~/tems/
├── tems.py            # Backend + CLI
├── tems_tui.py        # TUI (CSS embedded — no .tcss needed)
├── tems.yaml          # Your config (keep permissions restricted)
└── merge_config.json  # Auto-generated on first xml-merge run
```

> **v0.5 note:** `tems_tui.tcss` is no longer required. If you have it from a previous version, it's safe to delete.

---

## Secure Your Config

```bash
chmod 600 tems.yaml
```

---

## Automated Updates via Cron

```bash
crontab -e
```

```bash
# Daily mod updates at 4 AM
0 4 * * * /home/yourusername/tems/tems.py update --yes >> /home/yourusername/logs/mod-updates.log 2>&1

# Daily backup at 4:30 AM
30 4 * * * /home/yourusername/tems/tems.py backup --yes >> /home/yourusername/logs/tems-backup.log 2>&1
```

Set defaults in `tems.yaml` for cron:
```yaml
backup_default_scope: "world,configs"
backup_default_dest: "local"
```

---

## Updating TEMS

```bash
cd ~/tems
git pull
```

Or replace `tems.py` and `tems_tui.py` manually — your `tems.yaml` and `merge_config.json` are preserved.

---

## Uninstallation

```bash
rm -rf ~/tems
crontab -e  # remove tems lines
rm ~/.dayz_mod_mapping  # optional
```

Your installed mods and server config are untouched.
