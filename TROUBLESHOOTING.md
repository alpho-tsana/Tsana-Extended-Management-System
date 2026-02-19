# Troubleshooting Guide

Solutions for common TEMS v0.5 issues.

---

## TUI Issues

### TUI won't launch / ModuleNotFoundError

```bash
pip install textual requests --break-system-packages
python3 tems_tui.py
```

Use `python3` explicitly rather than `./tems_tui.py` if the shebang points to a different Python.

### "object has no attribute 'call_from_thread'"

This was a bug in v0.3 where worker threads called `self.call_from_thread` instead of `self.app.call_from_thread`. Fixed in v0.5.

### Status panel shows "—" for everything

TEMS couldn't read your config or mapping file. Check that `tems.yaml` exists and `mod_mapping_file` path is correct:
```bash
ls ~/.dayz_mod_mapping
```

### tems_tui.tcss not found error

From v0.5, `tems_tui.tcss` is no longer needed — styles are embedded in `tems_tui.py`. Delete the old `.tcss` file if you have it, or simply ignore the error if running the new version.

---

## Workshop Download Issues

### ERROR! Download item XXXXXX failed (Failure)

Common causes: invalid ID, Steam auth issues, rate limiting, disk space full.

```bash
# Check disk space (need at least 5GB free)
df -h

# Validate the ID manually
curl -I "https://steamcommunity.com/sharedfiles/filedetails/?id=WORKSHOP_ID"

# Use manual install if download keeps failing
python3 tems.py install --manual
```

### Steam Guard / 2FA

SteamCMD remembers sessions for ~24 hours. On first run you'll be prompted for the 2FA code. For cron automation, use a dedicated account without 2FA.

### Rate Limiting

Use batch-install for multiple mods — it downloads in a single SteamCMD session:
```bash
python3 tems.py batch-install my_mod_list.txt
```

---

## Server Startup Failures

### Server crashes after adding mods

```bash
# Check logs
tail -100 ~/.local/share/dayzserver/console/dayzserver-console.log
grep -i "script.*e):" dayzserver-console.log
```

**Missing dependencies:** Install CF, DabsFramework, Expansion-Core before mods that require them.

**Load order:** Use `python3 tems.py reorder`. Correct order:
1. Map mods (`@Banov`, etc.)
2. Framework mods (`@CF`, `@DabsFramework`)
3. `@DayZ-Expansion-Core`
4. Other Expansion mods
5. Feature mods
6. Admin tools last

**Mod conflicts:**
```
Conflicting addon X in 'modA', previous definition in 'modB'
```
Remove one of the conflicting mods via `python3 tems.py cleanup`.

---

## File Permission Errors

```bash
# Fix mods directory ownership
sudo chown -R username:username ~/serverfiles
chmod 755 ~/serverfiles/mods

# Fix LGSM config
chmod 644 ~/lgsm/config-lgsm/dayzserver/dayzserver.cfg
```

---

## XML Merge Issues

### "No mods found" on quick merge

Check `mod_search_paths` in `merge_config.json` points to the right directory:
```bash
ls ~/serverfiles/mods/
```

Regenerate config if needed:
```bash
rm merge_config.json
python3 tems.py xml-merge
```

### XML merge creates duplicates

Verify `overwrite_existing` is `false` in `merge_config.json` (the default). TEMS checks for existing entries by name before adding.

### Restore from XML backup

```bash
ls ~/tems/xml_backups/
cp ~/tems/xml_backups/types.xml.YYYYMMDD_HHMMSS.bak \
   ~/serverfiles/mpmissions/empty.banov/db/types.xml
```

---

## Backup Issues

### rclone upload fails

```bash
curl https://rclone.org/install.sh | sudo bash
rclone config
rclone lsd your-remote:
```

Then set `backup_rclone_remote: "your-remote:dayz-backups"` in `tems.yaml`.

### Backup fills disk

```bash
# Reduce retention in tems.yaml
backup_keep: 3

# Check backup directory
du -sh ~/backups/tems/
```

---

## Config Issues

### tems.yaml not found

TEMS looks in the same directory as `tems.py`. Use `--config` if elsewhere:
```bash
python3 tems.py --config /path/to/tems.yaml
```

### Paths don't exist

```bash
mkdir -p ~/serverfiles/mods
mkdir -p ~/serverfiles/keys
```

---

## Preventive Maintenance

**Weekly:**
```bash
df -h
python3 tems.py update
./dayzserver restart
```

**Monthly:**
```bash
python3 tems.py export -o backup_$(date +%Y%m%d).txt
python3 tems.py reorder
find ~/log -name "*.log" -mtime +30 -delete
find ~/tems/xml_backups/ -name "*.bak" -mtime +60 -delete
```

---

**Still stuck?** Open an issue with TEMS version, full error, steps to reproduce, and server details (OS, LinuxGSM version, mods installed).
