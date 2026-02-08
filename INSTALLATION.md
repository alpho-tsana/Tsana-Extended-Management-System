# Installation Guide

Setup instructions for TEMS - Tsana Extended Management System v0.2.

---

## Prerequisites

### Required Software
- **Linux Server** - Ubuntu 20.04+ or Debian 10+ recommended
- **Python 3.10+** - Check with: `python3 --version`
- **LinuxGSM DayZ Server** - [Installation guide](https://linuxgsm.com/servers/dayzserver/)
- **SteamCMD** - Installed automatically with LinuxGSM
- **Steam Account** - Does NOT need to own DayZ
- **rclone** *(optional)* - Only needed for cloud backups. [Install guide](https://rclone.org/install/)

### Server Access
- SSH access to your server
- Sudo privileges (for initial setup only)
- Ability to upload/download files (SCP, SFTP, or WinSCP)

---

## Step-by-Step Installation

### 1. Download TEMS

**Method A: Git Clone (Recommended)**
```bash
cd ~
git clone https://github.com/EngineerAlpho/dayz-mod-scripts.git tems
cd tems
```

**Method B: Direct Download**
```bash
cd ~
mkdir tems
cd tems
# Upload tems.py and tems.yaml here via SFTP/WinSCP
```

### 2. Verify Python

```bash
python3 --version
# Should show 3.10 or higher
```

TEMS uses only Python standard library modules - no pip packages required.

### 3. Configure Settings

Edit the configuration file:
```bash
nano tems.yaml
```

**Required Changes:**
```yaml
# Update these with your Steam credentials
steam_user: "your_steam_username"
steam_pass: "your_steam_password"
```

**Optional - Adjust Paths (if non-standard setup):**
```yaml
# Default paths work for standard LinuxGSM installation
# Only change if your server is in a different location
server_base_dir: "~"
server_files_dir: "~/serverfiles"
server_mods_dir: "~/serverfiles/mods"
keys_dir: "~/serverfiles/keys"
lgsm_config: "~/lgsm/config-lgsm/dayzserver/dayzserver.cfg"
```

Save and exit (Ctrl+X, Y, Enter).

### 4. Verify Configuration

Test that paths are correct:
```bash
# Check if server files directory exists
ls ~/serverfiles

# Check if LGSM config exists
ls ~/lgsm/config-lgsm/dayzserver/dayzserver.cfg
```

If these commands show errors, adjust paths in `tems.yaml` accordingly.

### 5. Test Installation

```bash
python3 tems.py
```

You should see the TEMS ASCII banner followed by the interactive menu:
```
  ████████╗ ███████╗ ███╗   ███╗ ███████╗
  ╚══██╔══╝ ██╔════╝ ████╗ ████║ ██╔════╝
     ██║    █████╗   ██╔████╔██║ ███████╗
     ██║    ██╔══╝   ██║╚██╔╝██║ ╚════██║
     ██║    ███████╗ ██║ ╚═╝ ██║ ███████║
     ╚═╝    ╚══════╝ ╚═╝     ╚═╝ ╚══════╝
  Tsana Extended Management System v0.2

  Choose a command:
    1. Install
    2. Batch Install
    3. Update
    4. Reorder
    5. Export
    6. Cleanup
    7. Backup
    8. XML Merge
    9. Exit
```

If you see this menu, installation is successful. Choose option 9 to exit.

Note: The menu now loops back after each action. You no longer need to re-launch the script after every command.

---

## Post-Installation Setup

### Secure Your Credentials

Restrict access to `tems.yaml`:
```bash
chmod 600 tems.yaml
```

### Make the Script Executable (Optional)

```bash
chmod +x tems.py
# Now you can run: ./tems.py instead of python3 tems.py
```

### Add to PATH (Optional)

For easier access from anywhere:
```bash
echo 'export PATH=$PATH:$HOME/tems' >> ~/.bashrc
source ~/.bashrc
```

### Set Up Automated Updates (Optional)

Add to crontab for automatic mod updates:
```bash
crontab -e
```

Add lines for daily 4 AM updates and backups:
```bash
0 4 * * * /home/yourusername/tems/tems.py update --yes >> /home/yourusername/logs/mod-updates.log 2>&1
30 4 * * * /home/yourusername/tems/tems.py backup --yes >> /home/yourusername/logs/tems-backup.log 2>&1
```

For automated backups, set defaults in `tems.yaml`:
```yaml
backup_default_scope: "world,configs"
backup_default_dest: "local"
```

---

## XML Merge Setup (Optional)

The XML Merge feature (formerly the standalone DMXM tool) is built in and requires no extra installation. On first use it will auto-generate a `merge_config.json` file using paths from your `tems.yaml`.

To get started:
```bash
# From the interactive menu, choose option 8
# Or run directly:
python3 tems.py xml-merge
```

The auto-detect feature will scan for mission folders and configure paths automatically. See [CONFIGURATION.md](CONFIGURATION.md) for manual configuration of `merge_config.json`.

---

## Custom Config Location

You can store `tems.yaml` anywhere and point to it:
```bash
python3 tems.py --config /path/to/custom/tems.yaml install
```

---

## Verification Checklist

After installation, verify everything works:

- [ ] Python 3.10+ is installed
- [ ] `tems.yaml` has correct Steam credentials
- [ ] Paths in `tems.yaml` point to existing directories
- [ ] `python3 tems.py` shows the interactive menu with 9 options
- [ ] `tems.yaml` has restricted permissions (600)
- [ ] Menu loops back after choosing a command (e.g., try option 6 then cancel)

---

## Updating TEMS

### Method A: Git Pull (if installed via Git)
```bash
cd ~/tems
git pull
```

### Method B: Manual Update
1. Download the new `tems.py`
2. **Backup your `tems.yaml` and `merge_config.json` first**
3. Replace `tems.py`
4. Verify `tems.yaml` settings are still valid

Your `tems.yaml` and `merge_config.json` are preserved during updates.

---

## Uninstallation

```bash
# Remove TEMS directory
rm -rf ~/tems

# Remove cron jobs (if set up)
crontab -e
# Delete the tems.py lines

# Optional: Remove mod mapping file
rm ~/.dayz_mod_mapping
```

Your installed mods and server config remain untouched.

---

## Next Steps

1. Read [CONFIGURATION.md](CONFIGURATION.md) for advanced options
2. Install your first mod: `python3 tems.py install`
3. Review [Common Workflows](README.md#common-workflows) in main README
4. Try the XML Merge: `python3 tems.py xml-merge`
5. Set up automated updates if desired
6. Export your mod list for backup: `python3 tems.py export`
