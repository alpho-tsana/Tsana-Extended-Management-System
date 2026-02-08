# Troubleshooting Guide

Solutions to common issues when using TEMS v0.3.

---

## Table of Contents

1. [Workshop Download Issues](#workshop-download-issues)
2. [Disk Space Problems](#disk-space-problems)
3. [Server Startup Failures](#server-startup-failures)
4. [Mod Compatibility Issues](#mod-compatibility-issues)
5. [File Permission Errors](#file-permission-errors)
6. [Configuration Problems](#configuration-problems)
7. [Backup Issues](#backup-issues)
8. [XML Merge Issues](#xml-merge-issues)
9. [Trader Setup Issues](#trader-setup-issues)

---

## Workshop Download Issues

### ERROR! Download item XXXXXX failed (Failure)

**Symptoms:**
```
Downloading item 2878980498 ...
ERROR! Download item 2878980498 failed (Failure).
```

**Common Causes:**
1. Invalid Workshop ID
2. Steam authentication issues
3. Rate limiting from Steam
4. Disk space full
5. Mod requires special permissions

**Solutions:**

**Step 1: Validate Workshop ID**
```bash
# TEMS validates IDs automatically, but you can check manually:
curl -I "https://steamcommunity.com/sharedfiles/filedetails/?id=WORKSHOP_ID"
# Should return HTTP 200 if valid
```

**Step 2: Check Disk Space**
```bash
df -h
# Ensure at least 5GB free
```

**Step 3: Use Manual Installation**
```bash
# Download via Steam client on your PC
# Upload to ~/serverfiles/mods/@ModName
python3 tems.py install --manual
```

**Step 4: Wait and Retry**
Steam Workshop sometimes has temporary issues. Wait 10-15 minutes and try again.

### Rate Limiting

**Symptoms:**
- Multiple download failures in short time
- "Rate Limit Exceeded" messages

**Solution:**
```bash
# Use batch-install which downloads in one SteamCMD session
python3 tems.py batch-install mod_list.txt
# Wait 30-60 minutes between bulk downloads if needed
```

### Steam Guard / 2FA Issues

**Symptoms:**
- Prompted for Steam Guard code every time
- Login fails despite correct credentials

**Solution:**
```bash
# First run - enter 2FA code when prompted
python3 tems.py install
# SteamCMD will remember session for ~24 hours

# For automated scripts (cron), use a dedicated account without 2FA
```

---

## Disk Space Problems

### Workshop Files Filling Disk

**Symptoms:**
```
df -h
# Shows 95%+ disk usage
```

**Note:** TEMS automatically cleans up Workshop downloads after copying. If you have leftover files from the old shell scripts:

```bash
# Check Workshop folder size
du -sh ~/.local/share/Steam/steamapps/workshop/content/221100/

# Clean up (mods already copied to server)
rm -rf ~/.local/share/Steam/steamapps/workshop/content/221100/*

# Verify freed space
df -h
```

### Server Won't Start - Disk Full

**Symptoms:**
```
Server fails to start
Logs show "No space left on device"
```

**Solution:**
```bash
# Find what's using space
du -sh /* | sort -h
du -sh ~/serverfiles/* | sort -h

# Common culprits:
# - Workshop downloads (cleaned automatically by TEMS)
# - Server logs
# - Backup files
# - XML backup files (in xml_backups/)

# Clean old server logs
find ~/log -name "*.log" -mtime +30 -delete

# Clean old XML merge backups
ls -la ~/tems/xml_backups/
# Remove old .bak files if needed
```

---

## Server Startup Failures

### Server Crashes Immediately After Adding Mods

**Diagnostic Steps:**

**Step 1: Check Server Logs**
```bash
./dayzserver details
# Or
tail -100 ~/.local/share/dayzserver/console/dayzserver-console.log
```

**Step 2: Look for Script Errors**
```bash
grep -i "script.*e):" dayzserver-console.log
```

### Common Crash Causes

#### 1. Missing Mod Dependencies

**Error:**
```
Unknown type 'SomeModClass'
Can't compile "World" script module!
```

**Solution:**
- Check mod requirements on its Workshop page
- Install all dependencies first
- Common dependencies: CF, DabsFramework, Expansion-Core

#### 2. Incorrect Load Order

**Solution:**
```bash
python3 tems.py reorder
# Follow best practices:
# 1. Map mods first (@Banov, etc.)
# 2. Framework mods (@CF, @DabsFramework)
# 3. Core mods (@DayZ-Expansion-Core)
# 4. Feature mods
# 5. Admin tools last
```

#### 3. Incompatible Mod Versions

**Solution:**
- Update all mods: `python3 tems.py update`
- Check mod Workshop pages for compatibility notes
- Test mods individually

#### 4. Conflicting Mods

**Error:**
```
Conflicting addon X in 'modA', previous definition in 'modB'
```

**Solution:**
- Remove one of the conflicting mods via `python3 tems.py cleanup`
- Check for compatibility patches
- Choose one mod over the other

### Case Study: RaG + Expansion Conflict

**Problem:** Server crashed after adding RaG_BaseItems and DismantleFixExpansion

**Error:**
```
Unknown type 'ActionDismantleragbaseitem'
Can't compile "World" script module!
```

**Solution:**
1. Ensure RaG_Core loads first
2. Then RaG_BaseItems
3. Then DayZ-Expansion-Core
4. Finally DismantleFixExpansion
5. Use `python3 tems.py reorder` to fix the order

---

## Mod Compatibility Issues

### RaG_BaseItems Won't Download

**Problem:** Workshop download fails every time

**Solution:**
```bash
# This mod often fails via SteamCMD. Use manual installation:
# 1. Subscribe in Steam Workshop (browser or client)
# 2. Download via Steam client
# 3. Upload to ~/serverfiles/mods/@RaG_BaseItems
# 4. Run:
python3 tems.py install --manual
```

### Expansion Mods Need Specific Order

**Correct Order:**
```
@DayZ-Expansion-Core          # Always first
@DayZ-Expansion-Licensed      # Second
@DayZ-Expansion-Market        # Third
@DayZ-Expansion-AI
@DayZ-Expansion-Vehicles
@DayZ-Expansion-BaseBuilding
# ... other Expansion mods
```

**Fix with:**
```bash
python3 tems.py reorder
```

---

## File Permission Errors

### Cannot Write to Mods Directory

**Error:**
```
Permission denied: /home/username/serverfiles/mods
```

**Solution:**
```bash
# Check ownership
ls -la ~/serverfiles

# Fix ownership
sudo chown -R username:username ~/serverfiles

# Fix permissions
chmod 755 ~/serverfiles/mods
```

### Config File Not Writable

**Error:**
```
Permission denied when writing to LGSM config
```

**Solution:**
```bash
# Check LGSM config permissions
ls -la ~/lgsm/config-lgsm/dayzserver/dayzserver.cfg

# Fix if needed
chmod 644 ~/lgsm/config-lgsm/dayzserver/dayzserver.cfg
```

---

## Configuration Problems

### Config File Not Found

TEMS looks for `tems.yaml` in the same directory as `tems.py`.

**Solution:**
```bash
# Ensure tems.yaml is in the same directory
ls -la tems.yaml tems.py

# Or specify a custom path
python3 tems.py --config /path/to/tems.yaml
```

### Paths Don't Exist

**Error:**
```
Error: Mods directory not found: /path/to/mods
```

**Solution:**
```bash
# Create missing directories
mkdir -p ~/serverfiles/mods
mkdir -p ~/serverfiles/keys
```

---

## Backup Issues

### Backup Archive Is Empty or Missing Files

**Symptoms:**
- Backup completes but archive is very small
- Expected files not in the archive

**Solution:**
```bash
# Check that paths in tems.yaml are correct
ls ~/serverfiles/mpmissions/dayzOffline.chernarusplus
ls ~/serverfiles/mods

# Update mission_dir in tems.yaml if your map is different:
mission_dir: "~/serverfiles/mpmissions/empty.banov"
```

### rclone Upload Fails

**Symptoms:**
```
Error: rclone is not installed or not in PATH
```

**Solution:**
```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure a remote
rclone config

# Test connectivity
rclone lsd your-remote:

# Set the remote in tems.yaml
backup_rclone_remote: "your-remote:dayz-backups"
```

### LinuxGSM Full Backup Fails

**Symptoms:**
```
Error: LinuxGSM script not found
```

**Solution:**
```bash
# Find your LinuxGSM script
which dayzserver
ls ~/dayzserver

# Update lgsm_script in tems.yaml
lgsm_script: "~/dayzserver"
```

### Backup Fills Disk

**Solution:**
```bash
# Reduce the number of retained backups in tems.yaml
backup_keep: 3

# Check backup directory size
du -sh ~/backups/tems/

# Manually remove old backups
ls -lt ~/backups/tems/
rm ~/backups/tems/tems_backup_old_*.tar.gz
```

---

## XML Merge Issues

### "No mods found" When Running Quick Merge

**Symptoms:**
- XML Merge scans but finds no mods

**Causes:**
- `mod_search_paths` in `merge_config.json` points to the wrong directory
- Mod folders don't start with `@`

**Solution:**
```bash
# Check where your mods actually are
ls ~/serverfiles/mods/

# Edit merge_config.json and fix mod_search_paths
nano merge_config.json
# Or delete it to regenerate from tems.yaml defaults:
rm merge_config.json
python3 tems.py xml-merge
```

### "No mission folders found" During Auto-detect

**Symptoms:**
- Auto-detect runs but doesn't find any missions

**Causes:**
- Mission folders are in a non-standard location
- Missing `db/types.xml` or `cfgeventspawns.xml` in the mission folder

**Solution:**
```bash
# Find your mission folders
ls ~/serverfiles/mpmissions/

# Manually add via the Manage missions submenu (option 6 in XML Merge)
# Or edit merge_config.json directly
```

### XML Merge Creates Duplicates

**Symptoms:**
- Running merge multiple times adds the same entries again

**Cause:**
- This shouldn't happen - TEMS checks for existing entries by name before adding. If `overwrite_existing` is `false` (the default), duplicates are skipped.

**Solution:**
```bash
# Verify merge settings via XML Merge menu option 7
# Ensure "Overwrite existing" is OFF

# If duplicates already exist, restore from backup:
ls ~/tems/xml_backups/
# Copy the .bak file back to the original location
cp ~/tems/xml_backups/types.xml.20250207_143000.bak ~/serverfiles/mpmissions/empty.banov/db/types.xml
```

### XML Parse Error During Merge

**Symptoms:**
```
Warning: Could not parse /path/to/types.xml: ...
```

**Causes:**
- Malformed XML in the mod file
- File encoding issues

**Solution:**
```bash
# Validate the XML file
python3 -c "import xml.etree.ElementTree as ET; ET.parse('/path/to/file.xml')"

# If it fails, the mod's XML file is malformed
# Try re-downloading the mod or fixing the XML manually
```

### Wrong Mission Selected for Merge

**Symptoms:**
- Merge goes into the wrong mission folder

**Solution:**
```bash
# Check active mission in the XML Merge menu header
# Use option 4 (Switch mission) to change it
# Or edit merge_config.json and set "active_mission"
```

### XML Backup Folder Growing Large

**Symptoms:**
- `xml_backups/` folder uses significant disk space

**Solution:**
```bash
# Check size
du -sh ~/tems/xml_backups/

# Remove old backups (keep recent ones)
find ~/tems/xml_backups/ -name "*.bak" -mtime +30 -delete

# Or disable backups via XML Merge menu option 7
```

---

## Trader Setup Issues

### Trader NPC Spawns But Isn't Functional

**Common Causes:**

**1. Trader JSON File Missing**
```bash
# Check if trader config exists
ls ~/serverfiles/profiles/ExpansionMod/Traders/
# Must have matching JSON file for each trader type
```

**2. Trader Type Mismatch**
```
# In .map file, trader type MUST match JSON filename exactly
# Including underscores and capitalization
```

**3. Trader Not In Safe Zone**
```bash
# Verify trader coordinates are within a defined zone
cat ~/serverfiles/mpmissions/empty.banov/expansion/traderzones/World.json
```

### Trader NPCs Are Naked

**Cause:** Invalid clothing class names or slot conflicts

**Working Combinations:**
- Jeans + TShirt + WorkingBoots
- CargoPants + TacticalShirt + MilitaryBoots
- Avoid: Coveralls (top + bottom = slot conflict)

---

## Advanced Diagnostics

### Check SteamCMD Directly

```bash
~/.steam/steamcmd/steamcmd.sh +login username password +workshop_download_item 221100 WORKSHOP_ID +quit
```

### Verify Mod Structure

```bash
# Expected structure:
@ModName/
  addons/
    *.pbo files
  keys/
    *.bikey files
  mod.cpp (optional)

# Check an installed mod:
ls -la ~/serverfiles/mods/@ModName/
```

### Check What XML Files a Mod Contains

```bash
# Use the XML Merge "List mods" option (option 3) to see which mods
# have types.xml, events.xml, or spawnabletypes.xml files
python3 tems.py xml-merge
# Then choose option 3
```

---

## Preventive Maintenance

### Weekly Checks

```bash
# Check disk space
df -h

# Update mods
python3 tems.py update

# Verify server starts
./dayzserver restart
```

### Daily (or Automated)

```bash
# Back up world data and configs
python3 tems.py backup --scope world,configs --dest local --yes
```

### Monthly Tasks

```bash
# Export mod list backup
python3 tems.py export -o backup_$(date +%Y%m%d).txt

# Full backup including mods
python3 tems.py backup --scope world,mods,configs --dest local,rclone

# Review and optimize load order
python3 tems.py reorder

# Clean old logs
find ~/log -name "*.log" -mtime +30 -delete

# Clean old XML merge backups
find ~/tems/xml_backups/ -name "*.bak" -mtime +60 -delete
```

---

**Still need help?** Open an issue with:
- TEMS version (check banner output - should show v0.3)
- Full error message
- Steps to reproduce
- Server details (OS, LinuxGSM version, mods installed)
