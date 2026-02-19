# Configuration Guide

Reference for TEMS v0.5 configuration files.

---

## Overview

| File | Purpose | Format |
|------|---------|--------|
| `tems.yaml` | Main config: Steam credentials, server paths, backup settings | YAML |
| `merge_config.json` | XML Merge config: missions, mod search paths, merge rules | JSON |

---

## tems.yaml — Full Reference

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

### Settings Reference

| Key | Default | Description |
|-----|---------|-------------|
| `steam_user` | — | Steam account username |
| `steam_pass` | — | Steam account password |
| `server_base_dir` | `~` | Root server directory |
| `server_files_dir` | `~/serverfiles` | LinuxGSM server files |
| `server_mods_dir` | `~/serverfiles/mods` | Installed mods directory |
| `keys_dir` | `~/serverfiles/keys` | .bikey files directory |
| `lgsm_config` | `~/lgsm/config-lgsm/dayzserver/dayzserver.cfg` | LinuxGSM config file |
| `steamcmd_path` | `~/.steam/steamcmd/steamcmd.sh` | SteamCMD executable |
| `workshop_dir` | `~/.local/share/Steam/steamapps/workshop/content/221100` | Workshop download location |
| `mod_mapping_file` | `~/.dayz_mod_mapping` | Workshop ID → mod name mapping |
| `dayz_app_id` | `221100` | DayZ Steam App ID (do not change) |
| `backup_dir` | `~/backups/tems` | Local backup storage |
| `backup_rclone_remote` | `""` | rclone remote (e.g. `gdrive:dayz-backups`) |
| `backup_keep` | `5` | Local backups to retain (0 = unlimited) |
| `backup_default_scope` | `""` | Default scope for `--yes` mode |
| `backup_default_dest` | `""` | Default destination for `--yes` mode |
| `mission_dir` | `~/serverfiles/mpmissions/dayzOffline.chernarusplus` | Active mission directory |
| `lgsm_script` | `~/dayzserver` | LinuxGSM server script path |

**Backup scopes:** `world`, `mods`, `configs`, `full`

**Restrict permissions:**
```bash
chmod 600 tems.yaml
```

---

## merge_config.json — Full Reference

Auto-generated on first `xml-merge` run.

```json
{
    "backup_enabled": true,
    "backup_folder": "./backups",
    "active_mission": "empty.banov",
    "missions": {
        "empty.banov": {
            "types": "/home/banov1/serverfiles/mpmissions/empty.banov/db/types.xml",
            "events": "/home/banov1/serverfiles/mpmissions/empty.banov/cfgeventspawns.xml",
            "spawnabletypes": "/home/banov1/serverfiles/mpmissions/empty.banov/db/spawnabletypes.xml"
        }
    },
    "mod_search_paths": [
        "~/serverfiles/mods"
    ],
    "merge_rules": {
        "skip_vanilla_duplicates": true,
        "overwrite_existing": false,
        "preserve_comments": true
    }
}
```

| Key | Default | Description |
|-----|---------|-------------|
| `backup_enabled` | `true` | Backup XML files before merging |
| `backup_folder` | `./backups` | XML backup location |
| `active_mission` | auto-detected | Mission to merge into |
| `merge_rules.overwrite_existing` | `false` | Replace existing entries |
| `merge_rules.skip_vanilla_duplicates` | `true` | Skip vanilla entries |
| `merge_rules.preserve_comments` | `true` | Keep XML comments |

To reset: `rm merge_config.json` — TEMS will regenerate it from `tems.yaml`.

---

## Multi-Server Setup

```bash
python3 tems.py --config server1.yaml update
python3 tems.py --config server2.yaml update
```

Note: `merge_config.json` is always read from the same directory as `tems.py`.

---

## Security

```bash
# Restrict tems.yaml to owner only
chmod 600 tems.yaml

# Add to .gitignore
echo "tems.yaml" >> .gitignore
echo "merge_config.json" >> .gitignore
```
