# Configuration Guide

Reference for configuration files used by TEMS v0.3.

---

## Overview

TEMS uses two configuration files:

| File | Purpose | Format |
|------|---------|--------|
| `tems.yaml` | Main config: Steam credentials, server paths, backup settings | YAML (key: value) |
| `merge_config.json` | XML Merge config: missions, mod search paths, merge rules | JSON |

Both files live in the same directory as `tems.py` by default.

- **Edit once, use everywhere** - All subcommands share the same config
- **Tilde expansion** - `~` in paths within `tems.yaml` expands to your home directory
- **Sensible defaults** - Works out of the box with standard LinuxGSM installations
- **Auto-generated** - `merge_config.json` is created automatically on first use of `xml-merge`

---

## tems.yaml - Full Reference

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

---

## tems.yaml Settings Breakdown

### Steam Credentials

```yaml
steam_user: "your_username"
steam_pass: "your_password"
```

**Required:** Yes

**Steam Guard:** If you have 2FA enabled, you'll be prompted for the code on first SteamCMD run. SteamCMD remembers the session for ~24 hours.

**Recommendations:**
- Use a dedicated Steam account for server management
- Don't use your main gaming account
- Account does NOT need to own DayZ

### Server Paths

```yaml
server_base_dir: "~"
server_files_dir: "~/serverfiles"
server_mods_dir: "~/serverfiles/mods"
keys_dir: "~/serverfiles/keys"
lgsm_config: "~/lgsm/config-lgsm/dayzserver/dayzserver.cfg"
```

| Key | Purpose | Default |
|-----|---------|---------|
| `server_base_dir` | Root server directory | `~` |
| `server_files_dir` | LinuxGSM server files | `~/serverfiles` |
| `server_mods_dir` | Where mods are installed | `~/serverfiles/mods` |
| `keys_dir` | Where .bikey files are copied | `~/serverfiles/keys` |
| `lgsm_config` | LinuxGSM DayZ config file | `~/lgsm/config-lgsm/dayzserver/dayzserver.cfg` |

Only change these if your server is in a non-standard location.

### SteamCMD Paths

```yaml
steamcmd_path: "~/.steam/steamcmd/steamcmd.sh"
workshop_dir: "~/.local/share/Steam/steamapps/workshop/content/221100"
```

| Key | Purpose | Default |
|-----|---------|---------|
| `steamcmd_path` | Path to SteamCMD executable | `~/.steam/steamcmd/steamcmd.sh` |
| `workshop_dir` | Where SteamCMD downloads workshop items | `~/.local/share/Steam/steamapps/workshop/content/221100` |

### Mod Management

```yaml
mod_mapping_file: "~/.dayz_mod_mapping"
dayz_app_id: 221100
```

| Key | Purpose | Default |
|-----|---------|---------|
| `mod_mapping_file` | Tracks Workshop ID to @ModName mappings | `~/.dayz_mod_mapping` |
| `dayz_app_id` | DayZ Steam App ID (don't change) | `221100` |

The mapping file format is:
```
2415195639:@Banov
2116151222:@DayZ-Expansion-Core
```

### Backup Settings

```yaml
backup_dir: "~/backups/tems"
backup_rclone_remote: ""
backup_keep: 5
backup_default_scope: ""
backup_default_dest: ""
mission_dir: "~/serverfiles/mpmissions/dayzOffline.chernarusplus"
lgsm_script: "~/dayzserver"
```

| Key | Purpose | Default |
|-----|---------|---------|
| `backup_dir` | Where local backup archives are stored | `~/backups/tems` |
| `backup_rclone_remote` | rclone remote destination (e.g., `gdrive:dayz-backups`) | `""` (disabled) |
| `backup_keep` | Number of local backups to retain (0 = unlimited) | `5` |
| `backup_default_scope` | Default scope for `--yes` mode (e.g., `world,configs`) | `""` |
| `backup_default_dest` | Default destination for `--yes` mode (e.g., `local,rclone`) | `""` |
| `mission_dir` | Path to mission/world data directory | `~/serverfiles/mpmissions/dayzOffline.chernarusplus` |
| `lgsm_script` | Path to LinuxGSM server script | `~/dayzserver` |

**Backup scopes:** `world`, `mods`, `configs`, `full` (LinuxGSM native)

**Setting up rclone:**
```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure a remote (interactive wizard)
rclone config

# Test the remote
rclone lsd your-remote:
```

**Cron example (automated daily backup):**
```yaml
# Set defaults in tems.yaml:
backup_default_scope: "world,configs"
backup_default_dest: "local"
```
```bash
# Add to crontab:
0 4 * * * /home/yourusername/tems/tems.py backup --yes >> /var/log/tems_backup.log 2>&1
```

---

## merge_config.json - Full Reference

This file is auto-generated on first use of the `xml-merge` command. It controls how mod XML files are merged into your server's mission folders.

```json
{
    "backup_enabled": true,
    "backup_folder": "/home/yourusername/tems/xml_backups",
    "active_mission": "dayzOffline.chernarusplus",
    "missions": {
        "dayzOffline.chernarusplus": {
            "types": "/home/yourusername/serverfiles/mpmissions/dayzOffline.chernarusplus/db/types.xml",
            "events": "/home/yourusername/serverfiles/mpmissions/dayzOffline.chernarusplus/cfgeventspawns.xml",
            "spawnabletypes": "/home/yourusername/serverfiles/mpmissions/dayzOffline.chernarusplus/db/spawnabletypes.xml"
        }
    },
    "mod_search_paths": [
        "/home/yourusername/serverfiles/mods"
    ],
    "merge_rules": {
        "skip_vanilla_duplicates": true,
        "overwrite_existing": false,
        "preserve_comments": true
    }
}
```

### merge_config.json Settings Breakdown

#### General

| Key | Purpose | Default |
|-----|---------|---------|
| `backup_enabled` | Create backups of XML files before merging | `true` |
| `backup_folder` | Where XML backups are stored | `xml_backups/` (next to tems.py) |
| `active_mission` | Which mission folder to merge into | Auto-detected from `tems.yaml` `mission_dir` |

#### Missions

Each mission entry maps a mission name to its XML file paths. You can configure multiple missions and switch between them.

```json
"missions": {
    "dayzOffline.chernarusplus": {
        "types": "/path/to/mpmissions/dayzOffline.chernarusplus/db/types.xml",
        "events": "/path/to/mpmissions/dayzOffline.chernarusplus/cfgeventspawns.xml",
        "spawnabletypes": "/path/to/mpmissions/dayzOffline.chernarusplus/db/spawnabletypes.xml"
    },
    "empty.banov": {
        "types": "/path/to/mpmissions/empty.banov/db/types.xml",
        "events": "/path/to/mpmissions/empty.banov/cfgeventspawns.xml",
        "spawnabletypes": "/path/to/mpmissions/empty.banov/db/spawnabletypes.xml"
    }
}
```

Missions can be managed interactively via the XML Merge submenu (option 6 - Manage missions) or auto-detected (option 5 - Auto-detect).

#### Mod Search Paths

```json
"mod_search_paths": [
    "/home/yourusername/serverfiles/mods"
]
```

Directories where TEMS scans for mod folders (those starting with `@`). Defaults to the `server_mods_dir` from `tems.yaml`. You can add additional paths if mods are stored elsewhere.

Wildcards are supported: `"./@*"`, `"./workshop/content/221100/*"`

#### Merge Rules

| Key | Purpose | Default |
|-----|---------|---------|
| `overwrite_existing` | Replace existing entries when merging (if `false`, duplicates are skipped) | `false` |
| `skip_vanilla_duplicates` | Skip entries that already exist in vanilla XMLs | `true` |
| `preserve_comments` | Attempt to preserve XML comments during merge | `true` |

These can be toggled interactively via the XML Merge submenu (option 7 - Merge settings).

---

## Using a Custom Config

```bash
# Point to a specific tems.yaml config file
python3 tems.py --config /path/to/my-config.yaml install

# Useful for multi-server setups
python3 tems.py -c server1.yaml update
python3 tems.py -c server2.yaml update
```

Note: `merge_config.json` is always loaded from the same directory as `tems.py`, regardless of the `--config` flag.

---

## Multi-Server Setup

Create separate config files for each server:

```yaml
# server1.yaml
steam_user: "shared_account"
steam_pass: "shared_password"
server_base_dir: "/home/server1"
server_files_dir: "/home/server1/serverfiles"
server_mods_dir: "/home/server1/serverfiles/mods"
keys_dir: "/home/server1/serverfiles/keys"
lgsm_config: "/home/server1/lgsm/config-lgsm/dayzserver/dayzserver.cfg"
```

```yaml
# server2.yaml
steam_user: "shared_account"
steam_pass: "shared_password"
server_base_dir: "/home/server2"
server_files_dir: "/home/server2/serverfiles"
server_mods_dir: "/home/server2/serverfiles/mods"
keys_dir: "/home/server2/serverfiles/keys"
lgsm_config: "/home/server2/lgsm/config-lgsm/dayzserver/dayzserver.cfg"
```

---

## Security Best Practices

### File Permissions

```bash
# Restrict tems.yaml to owner only (contains credentials)
chmod 600 tems.yaml
```

### Credential Management

**Don't:**
- Commit `tems.yaml` to public repositories
- Share `tems.yaml` with credentials included

**Do:**
- Add `tems.yaml` to `.gitignore`
- Use a dedicated service Steam account

**.gitignore example:**
```
tems.yaml
merge_config.json
*.log
.dayz_mod_mapping
__pycache__/
xml_backups/
```

---

## Troubleshooting Configuration

### Test Your Config

```bash
# Quick test - does the menu load?
python3 tems.py

# If paths are wrong, you'll see errors like:
# Error: SteamCMD not found at /path/to/steamcmd.sh
# Error: Mods directory not found: /path/to/mods
```

### Common Issues

**Config file not found**
- Ensure `tems.yaml` is in the same directory as `tems.py`
- Or use `--config` to specify the path

**Paths don't exist**
- Verify LinuxGSM is installed correctly
- Create missing directories: `mkdir -p ~/serverfiles/mods`

**Permission denied**
- Check directory ownership: `ls -la ~/serverfiles`
- Ensure your user has write permissions

**merge_config.json has wrong paths**
- Delete it and let TEMS regenerate it: `rm merge_config.json`
- Or edit it manually / use the Manage missions submenu

---

## Next Steps

- Review [INSTALLATION.md](INSTALLATION.md) for setup
- Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues
