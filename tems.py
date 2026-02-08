#!/usr/bin/env python3
# =============================================================================
# TEMS - Tsana Extended Management System
# Version: 0.2
# Author: Engineer Alpho (with assistance from Claude/Anthropic)
# License: GPL-3.0
# Repository: https://github.com/EngineerAlpho/dayz-mod-scripts
# =============================================================================
#
# Consolidated tool replacing the individual shell scripts:
#   download_workshop_mod.sh, manual_mod_install.sh, batch_install_mods.sh,
#   update_all_mods.sh, reorder_mods.sh, export_mod_list.sh,
#   cleanup_mods_config.sh
#
# Now also includes DMXM (DayZ Mod XML Merger) functionality for merging
# mod types.xml, events.xml, and spawnabletypes.xml into server mission files.
#
# Usage:
#   tems.py                       → interactive menu (loops back after each action)
#   tems.py install               → install a single mod (workshop or manual)
#   tems.py batch-install FILE    → batch install from mod list file
#   tems.py update                → update all mapped mods
#   tems.py reorder               → interactive load order manager
#   tems.py export                → export mod list to file
#   tems.py cleanup               → remove mods from config
#   tems.py backup                → back up server data (local/cloud)
#   tems.py xml-merge             → merge mod XML files into server mission
#
# =============================================================================

import argparse
from datetime import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path


# ─── Version ────────────────────────────────────────────────────────────────

TEMS_VERSION = "0.2"


# ─── Config ──────────────────────────────────────────────────────────────────

class Config:
    """Loads tems.yaml (simple key: value format), expands ~ in paths."""

    DEFAULTS = {
        "steam_user": "",
        "steam_pass": "",
        "server_base_dir": "~",
        "server_files_dir": "~/serverfiles",
        "server_mods_dir": "~/serverfiles/mods",
        "keys_dir": "~/serverfiles/keys",
        "lgsm_config": "~/lgsm/config-lgsm/dayzserver/dayzserver.cfg",
        "steamcmd_path": "~/.steam/steamcmd/steamcmd.sh",
        "workshop_dir": "~/.local/share/Steam/steamapps/workshop/content/221100",
        "mod_mapping_file": "~/.dayz_mod_mapping",
        "dayz_app_id": "221100",
        "backup_dir": "~/backups/tems",
        "backup_rclone_remote": "",
        "backup_keep": "5",
        "backup_default_scope": "",
        "backup_default_dest": "",
        "mission_dir": "~/serverfiles/mpmissions/dayzOffline.chernarusplus",
        "lgsm_script": "~/dayzserver",
    }

    def __init__(self, config_path: Path | None = None):
        self._data = dict(self.DEFAULTS)

        if config_path is None:
            config_path = Path(__file__).resolve().parent / "tems.yaml"

        if config_path.exists():
            self._load(config_path)

        # Expand ~ in path-like values
        path_keys = {
            "server_base_dir", "server_files_dir", "server_mods_dir",
            "keys_dir", "lgsm_config", "steamcmd_path", "workshop_dir",
            "mod_mapping_file", "backup_dir", "mission_dir", "lgsm_script",
        }
        for key in path_keys:
            self._data[key] = str(Path(self._data[key]).expanduser())

    def _load(self, path: Path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r'^(\w+)\s*:\s*"?([^"]*)"?\s*$', line)
                if m:
                    self._data[m.group(1)] = m.group(2)

    def __getattr__(self, name: str) -> str:
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        try:
            return self._data[name]
        except KeyError:
            raise AttributeError(f"Config has no key '{name}'")


# ─── Colored output ─────────────────────────────────────────────────────────

class Colors:
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"

    @staticmethod
    def green(s):  return f"{Colors.GREEN}{s}{Colors.NC}"
    @staticmethod
    def yellow(s): return f"{Colors.YELLOW}{s}{Colors.NC}"
    @staticmethod
    def red(s):    return f"{Colors.RED}{s}{Colors.NC}"
    @staticmethod
    def blue(s):   return f"{Colors.BLUE}{s}{Colors.NC}"
    @staticmethod
    def cyan(s):   return f"{Colors.CYAN}{s}{Colors.NC}"


def banner(title: str):
    print(Colors.green("========================================"))
    print(Colors.green(f"  {title}"))
    print(Colors.green("========================================"))
    print()


def ascii_banner():
    logo = r"""
  ████████╗ ███████╗ ███╗   ███╗ ███████╗
  ╚══██╔══╝ ██╔════╝ ████╗ ████║ ██╔════╝
     ██║    █████╗   ██╔████╔██║ ███████╗
     ██║    ██╔══╝   ██║╚██╔╝██║ ╚════██║
     ██║    ███████╗ ██║ ╚═╝ ██║ ███████║
     ╚═╝    ╚══════╝ ╚═╝     ╚═╝ ╚══════╝
  Tsana Extended Management System v""" + TEMS_VERSION
    print(Colors.green(logo))
    print()


# ─── Interactive helpers ─────────────────────────────────────────────────────

def confirm(prompt: str, default: bool = False, auto_yes: bool = False) -> bool:
    if auto_yes:
        return True
    suffix = " (Y/n): " if default else " (y/n): "
    while True:
        ans = input(Colors.yellow(prompt + suffix)).strip().lower()
        if not ans:
            return default
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False
        print(Colors.red("Please answer y or n."))


def prompt_input(prompt: str) -> str:
    return input(Colors.yellow(prompt) + " ").strip()


def pause_before_menu():
    """Pause so the user can read output before returning to menu."""
    print()
    input(Colors.cyan("Press Enter to return to menu..."))


# ─── Shared utilities ────────────────────────────────────────────────────────

def lowercase_contents(mod_path: Path):
    """Recursively lowercase all files and dirs inside mod_path."""
    # Files first (bottom-up so renames don't break paths)
    for root, _dirs, files in os.walk(str(mod_path), topdown=False):
        root_path = Path(root)
        for name in files:
            lower = name.lower()
            if name != lower:
                src = root_path / name
                dst = root_path / lower
                try:
                    src.rename(dst)
                except OSError:
                    pass

    # Directories (bottom-up, skip the root mod dir itself)
    for root, dirs, _files in os.walk(str(mod_path), topdown=False):
        root_path = Path(root)
        for name in dirs:
            lower = name.lower()
            if name != lower:
                src = root_path / name
                dst = root_path / lower
                try:
                    src.rename(dst)
                except OSError:
                    pass


def copy_keys(mod_path: Path, keys_dir: Path):
    """Find and copy .bikey files from keys/Keys/key/Key dirs."""
    keys_dir.mkdir(parents=True, exist_ok=True)
    copied = False
    for key_dir_name in ("keys", "Keys", "key", "Key"):
        key_src = mod_path / key_dir_name
        if key_src.is_dir():
            for bikey in key_src.glob("*.bikey"):
                shutil.copy2(str(bikey), str(keys_dir / bikey.name))
                print(f"  {Colors.green('✓')} Copied: {bikey.name}")
                copied = True
    if not copied:
        print(Colors.yellow("  No .bikey files found (some mods don't require keys)"))


def read_lgsm_mods(config_path: Path) -> list[str]:
    """Parse mods= line from LGSM config, return list of @ModName strings."""
    if not config_path.exists():
        return []
    text = config_path.read_text()
    m = re.search(r'^mods="?(.*?)"?\s*$', text, re.MULTILINE)
    if not m or not m.group(1):
        return []
    raw = m.group(1)
    # Unescape \\; → ; and strip mods/ prefix
    raw = raw.replace("\\;", ";")
    parts = [p.strip() for p in raw.split(";") if p.strip()]
    mods = []
    for p in parts:
        # Strip mods/ prefix
        p = re.sub(r'^mods/', '', p)
        if p:
            mods.append(p)
    return mods


def write_lgsm_mods(config_path: Path, mods: list[str]):
    """Write mods list back to LGSM config with proper escaping."""
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Build the mods value: mods/@Mod1\\;mods/@Mod2
    if mods:
        parts = [f"mods/{m}" for m in mods]
        value = "\\;".join(parts)
    else:
        value = ""

    line = f'mods="{value}"'

    if config_path.exists():
        text = config_path.read_text()
        if re.search(r'^mods=', text, re.MULTILINE):
            text = re.sub(r'^mods=.*$', line, text, flags=re.MULTILINE)
        else:
            text = text.rstrip("\n") + "\n" + line + "\n"
        config_path.write_text(text)
    else:
        config_path.write_text(line + "\n")


def add_mod_to_config(config_path: Path, mod_name: str) -> bool:
    """Add a mod to LGSM config if not already present. Returns True if added."""
    mods = read_lgsm_mods(config_path)
    if mod_name in mods:
        print(Colors.yellow(f"  {mod_name} already in configuration"))
        return False
    mods.append(mod_name)
    write_lgsm_mods(config_path, mods)
    print(Colors.green(f"  ✓ Added {mod_name} to server mods"))
    return True


def read_mod_mapping(mapping_file: Path) -> dict[str, str]:
    """Read WORKSHOP_ID:@ModName mapping file → {id: name}."""
    result = {}
    if not mapping_file.exists():
        return result
    for line in mapping_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            wid, name = line.split(":", 1)
            result[wid.strip()] = name.strip()
    return result


def write_mod_mapping(mapping_file: Path, workshop_id: str, mod_name: str):
    """Append/update a mapping entry."""
    existing = {}
    if mapping_file.exists():
        for line in mapping_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                wid, name = line.split(":", 1)
                existing[wid.strip()] = name.strip()

    existing[workshop_id] = mod_name

    with open(mapping_file, "w") as f:
        for wid, name in existing.items():
            f.write(f"{wid}:{name}\n")


def run_steamcmd(config: Config, extra_args: list[str]):
    """Run SteamCMD with given arguments via subprocess."""
    cmd = [config.steamcmd_path] + extra_args
    subprocess.run(cmd)


def run_steamcmd_script(config: Config, script_lines: list[str]) -> int:
    """Write a temp script file and run SteamCMD with +runscript. Returns exit code."""
    fd, path = tempfile.mkstemp(prefix="tems_steamcmd_", suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            for line in script_lines:
                f.write(line + "\n")
        result = subprocess.run([config.steamcmd_path, "+runscript", path])
        return result.returncode
    finally:
        os.unlink(path)


def check_disk_space(path: str, warn_gb: int = 5):
    """Check available disk space and warn if low."""
    try:
        stat = os.statvfs(path)
        avail_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        print(Colors.blue(f"Available disk space: {avail_gb:.1f}GB"))
        if avail_gb < warn_gb:
            print(Colors.yellow(
                f"Warning: Less than {warn_gb}GB available. Large mods may fail to download."
            ))
        print()
    except OSError:
        pass


# ─── Backup helpers ────────────────────────────────────────────────────────

def gather_backup_paths(config: Config, scopes: list[str]) -> list[Path]:
    """Given a list of scopes (world, mods, configs), return source paths."""
    paths: list[Path] = []
    if "world" in scopes:
        mission = Path(config.mission_dir)
        if mission.is_dir():
            paths.append(mission)
        else:
            print(Colors.yellow(f"Warning: Mission dir not found: {mission}"))
    if "mods" in scopes:
        mods = Path(config.server_mods_dir)
        if mods.is_dir():
            paths.append(mods)
        else:
            print(Colors.yellow(f"Warning: Mods dir not found: {mods}"))
    if "configs" in scopes:
        # tems.yaml
        tems_yaml = Path(__file__).resolve().parent / "tems.yaml"
        if tems_yaml.exists():
            paths.append(tems_yaml)
        # LGSM config
        lgsm = Path(config.lgsm_config)
        if lgsm.exists():
            paths.append(lgsm)
        # Mod mapping
        mapping = Path(config.mod_mapping_file)
        if mapping.exists():
            paths.append(mapping)
        # Keys directory
        keys = Path(config.keys_dir)
        if keys.is_dir():
            paths.append(keys)
    return paths


def _get_total_size(paths: list[Path]) -> tuple[int, int]:
    """Walk source paths and return (total_bytes, file_count)."""
    total = 0
    count = 0
    for p in paths:
        if p.is_file():
            total += p.stat().st_size
            count += 1
        elif p.is_dir():
            for root, _dirs, files in os.walk(str(p)):
                for f in files:
                    try:
                        total += os.path.getsize(os.path.join(root, f))
                        count += 1
                    except OSError:
                        pass
    return total, count


def _format_size(nbytes: int) -> str:
    """Format byte count as human-readable string."""
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} TB"


def _print_progress_bar(current: int, total: int, width: int = 40):
    """Print a progress bar that overwrites the current line."""
    if total == 0:
        pct = 100.0
    else:
        pct = min(current / total * 100, 100.0)
    filled = int(width * current // max(total, 1))
    bar = "█" * filled + "░" * (width - filled)
    sys.stdout.write(f"\r  [{bar}] {pct:5.1f}% ({_format_size(current)} / {_format_size(total)})")
    sys.stdout.flush()


def create_backup_archive(source_paths: list[Path], dest_dir: Path, label: str) -> Path:
    """Create a timestamped .tar.gz of the given paths. Returns archive path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tems_backup_{label}_{timestamp}.tar.gz"
    archive_path = dest_dir / filename

    print(Colors.blue(f"Creating backup: {filename}"))

    total_bytes, file_count = _get_total_size(source_paths)
    print(Colors.blue(f"  {file_count} file(s), {_format_size(total_bytes)}"))
    print()

    processed_bytes = 0

    with tarfile.open(str(archive_path), "w:gz") as tar:
        for src in source_paths:
            base_arcname = src.name
            if src.is_file():
                tar.add(str(src), arcname=base_arcname)
                processed_bytes += src.stat().st_size
                _print_progress_bar(processed_bytes, total_bytes)
            elif src.is_dir():
                for root, dirs, files in os.walk(str(src)):
                    root_path = Path(root)
                    rel = root_path.relative_to(src)
                    tar.add(str(root_path), arcname=str(Path(base_arcname) / rel), recursive=False)
                    for f in files:
                        fpath = root_path / f
                        file_arcname = str(Path(base_arcname) / rel / f)
                        try:
                            fsize = fpath.stat().st_size
                            tar.add(str(fpath), arcname=file_arcname)
                            processed_bytes += fsize
                            _print_progress_bar(processed_bytes, total_bytes)
                        except OSError:
                            pass

    print()  # newline after progress bar
    size_mb = archive_path.stat().st_size / (1024 * 1024)
    print(Colors.green(f"✓ Backup created: {archive_path} ({size_mb:.1f} MB)"))
    return archive_path


def upload_rclone(archive_path: Path, remote: str) -> bool:
    """Upload archive to rclone remote. Returns True on success."""
    if not shutil.which("rclone"):
        print(Colors.red("Error: rclone is not installed or not in PATH"))
        print(Colors.yellow("Install rclone: https://rclone.org/install/"))
        return False

    print(Colors.blue(f"Uploading to rclone remote: {remote}"))
    result = subprocess.run(
        ["rclone", "copy", str(archive_path), remote, "--progress"],
    )
    if result.returncode == 0:
        print(Colors.green(f"✓ Uploaded to {remote}"))
        return True
    else:
        print(Colors.red(f"Error: rclone upload failed (exit code {result.returncode})"))
        return False


def rotate_backups(backup_dir: Path, keep: int):
    """Remove oldest tems_backup_*.tar.gz files, keeping the most recent `keep`."""
    if keep <= 0:
        return
    archives = sorted(
        backup_dir.glob("tems_backup_*.tar.gz"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if len(archives) > keep:
        print(Colors.blue(f"Rotating old backups (keeping {keep} most recent)..."))
        for old in archives[keep:]:
            old.unlink()
            print(f"  Removed: {Colors.yellow(old.name)}")


def run_lgsm_backup(config: Config):
    """Run ./dayzserver backup (LinuxGSM native full backup)."""
    lgsm = Path(config.lgsm_script)
    if not lgsm.exists():
        print(Colors.red(f"Error: LinuxGSM script not found: {lgsm}"))
        print(Colors.yellow("Set lgsm_script in tems.yaml to your dayzserver script path"))
        return False
    print(Colors.blue("Running LinuxGSM full backup..."))
    print()
    result = subprocess.run([str(lgsm), "backup"])
    if result.returncode == 0:
        print()
        print(Colors.green("✓ LinuxGSM backup completed"))
        return True
    else:
        print()
        print(Colors.red(f"Error: LinuxGSM backup failed (exit code {result.returncode})"))
        return False


def ensure_at_prefix(name: str) -> str:
    """Ensure mod name starts with @."""
    if not name.startswith("@"):
        return "@" + name
    return name


def validate_workshop_id(workshop_id: str) -> bool:
    """Check numeric format."""
    return bool(re.match(r"^\d+$", workshop_id))


def validate_workshop_id_online(workshop_id: str) -> str | None:
    """Check if workshop ID exists on Steam. Returns 'ok', 'not_found', or 'error'."""
    url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}"
    try:
        req = urllib.request.Request(url, method="HEAD")
        resp = urllib.request.urlopen(req, timeout=10)
        return "ok" if resp.status == 200 else "error"
    except urllib.error.HTTPError as e:
        return "not_found" if e.code == 404 else "error"
    except Exception:
        return "error"


def display_current_mods(config: Config):
    """Print the current mod list from LGSM config."""
    mods = read_lgsm_mods(Path(config.lgsm_config))
    if mods:
        print(Colors.blue("Current mods in config:"))
        for i, mod in enumerate(mods, 1):
            print(f"  {i}. {Colors.yellow(mod)}")
        print()
    return mods


def install_single_mod(workshop_id: str, mod_name: str, config: Config, auto_yes: bool = False):
    """Download a single workshop mod, copy, lowercase, key-copy, configure."""
    mod_name = ensure_at_prefix(mod_name)
    mod_name = mod_name.replace(" ", "")

    mods_dir = Path(config.server_mods_dir)
    mods_dir.mkdir(parents=True, exist_ok=True)
    keys_dir = Path(config.keys_dir)
    keys_dir.mkdir(parents=True, exist_ok=True)

    print(Colors.green(f"Downloading Workshop ID: {workshop_id}"))
    print(Colors.yellow("This may take a while depending on the mod size..."))
    print(Colors.yellow(f"Logging in as: {config.steam_user}"))
    print()

    # Run SteamCMD
    run_steamcmd(config, [
        "+login", config.steam_user, config.steam_pass,
        "+workshop_download_item", config.dayz_app_id, workshop_id,
        "+quit",
    ])

    workshop_path = Path(config.workshop_dir) / workshop_id
    dest_path = mods_dir / mod_name

    if not workshop_path.is_dir():
        print()
        print(Colors.red("Download failed!"))
        print("Please check:")
        print("- Workshop ID is correct")
        print("- Internet connection is stable")
        print("- SteamCMD has proper permissions")
        return False

    # Copy mod files
    print()
    print(Colors.blue("Copying mod files..."))
    if dest_path.exists():
        print(Colors.yellow(f"Warning: {mod_name} already exists. Removing old directory..."))
        shutil.rmtree(dest_path)

    shutil.copytree(str(workshop_path), str(dest_path))
    print(Colors.green(f"✓ Mod copied to: {dest_path}"))

    # Clean up workshop files
    print()
    print(Colors.blue("Cleaning up Workshop files..."))
    try:
        shutil.rmtree(workshop_path)
        print(Colors.green("✓ Workshop files cleaned up"))
    except OSError:
        print(Colors.yellow("Warning: Could not clean up Workshop files"))

    # Copy keys
    print()
    print(Colors.blue("Copying mod keys..."))
    copy_keys(dest_path, keys_dir)

    # Lowercase
    print()
    print(Colors.blue("Converting contents to lowercase..."))
    lowercase_contents(dest_path)
    print(Colors.green("✓ Contents converted to lowercase"))

    # Save mod mapping
    print()
    print(Colors.blue("Saving mod mapping..."))
    write_mod_mapping(Path(config.mod_mapping_file), workshop_id, mod_name)
    print(Colors.green("✓ Mod mapping saved"))

    # Update LGSM config
    print()
    print(Colors.blue("Updating server configuration..."))
    lgsm_path = Path(config.lgsm_config)
    if lgsm_path.exists():
        add_mod_to_config(lgsm_path, mod_name)
    else:
        print(Colors.yellow(f"Warning: LinuxGSM config not found at {config.lgsm_config}"))
        print(Colors.yellow("You'll need to manually add the mod to your startup parameters"))

    # Summary
    print()
    banner("Setup Complete!")
    print(Colors.blue("Mod Details:"))
    print(f"  Workshop ID: {Colors.yellow(workshop_id)}")
    print(f"  Mod Name: {Colors.yellow(mod_name)}")
    print(f"  Location: {Colors.yellow(str(dest_path))}")
    print()
    display_current_mods(config)

    return True


# ─── Commands ────────────────────────────────────────────────────────────────

def cmd_install(args, config: Config):
    """Interactive or flagged single mod install (workshop or manual)."""
    banner(f"DayZ Mod Installer v{TEMS_VERSION}")
    check_disk_space(str(Path.home()))

    # Check SteamCMD
    if not Path(config.steamcmd_path).exists():
        print(Colors.red(f"Error: SteamCMD not found at {config.steamcmd_path}"))
        return

    auto_yes = getattr(args, "yes", False)
    manual = getattr(args, "manual", False)

    # Show current mods
    display_current_mods(config)

    if manual:
        _do_manual_install(config, auto_yes)
        return

    # If workshop ID provided via CLI flag
    workshop_id = getattr(args, "workshop_id", None)
    mod_name = getattr(args, "name", None)

    if not workshop_id and not manual:
        # Interactive: choose workshop or manual
        print(Colors.yellow("Installation Method:"))
        print("  1. Download from Steam Workshop")
        print("  2. Install manually uploaded mod")
        print()
        choice = prompt_input("Choose option (1-2):")

        if choice == "2":
            _do_manual_install(config, auto_yes)
            return
        elif choice != "1":
            print(Colors.red("Invalid option"))
            return

        workshop_id = prompt_input("Enter the Workshop ID:")

    if not validate_workshop_id(workshop_id):
        print(Colors.red("Error: Invalid Workshop ID. Must be numeric."))
        return

    if not mod_name:
        mod_name = prompt_input(
            "Enter a name for this mod (e.g., @Banov, @CF, @DayZ-Expansion-Core):"
        )

    if not mod_name:
        print(Colors.red("Error: Mod name is required."))
        return

    success = install_single_mod(workshop_id, mod_name, config, auto_yes)

    if success and not auto_yes:
        while True:
            ans = prompt_input("Would you like to install another mod? (y/n):")
            if ans.lower() in ("y", "yes"):
                print()
                cmd_install(argparse.Namespace(
                    workshop_id=None, name=None, manual=False, yes=False
                ), config)
                return
            elif ans.lower() in ("n", "no"):
                print(Colors.green("All done! Don't forget to restart your server."))
                return
            else:
                print(Colors.red("Please answer y or n."))


def _do_manual_install(config: Config, auto_yes: bool):
    """Install a manually uploaded mod from the mods directory."""
    banner(f"Manual Mod Installation v{TEMS_VERSION}")

    mods_dir = Path(config.server_mods_dir)
    keys_dir = Path(config.keys_dir)
    lgsm_path = Path(config.lgsm_config)

    print(Colors.yellow("Instructions:"))
    print(f"1. Download the mod manually (from Steam Workshop browser or client)")
    print(f"2. Upload/copy the mod folder to: {Colors.blue(str(mods_dir))}")
    print(f"3. Name it with @ prefix (e.g., @RaG_BaseItems)")
    print()
    print(Colors.yellow(f"Available mods in {mods_dir}:"))
    print()

    if not mods_dir.is_dir():
        print(Colors.red(f"Error: Mods directory not found: {mods_dir}"))
        return

    available = sorted([d for d in mods_dir.iterdir() if d.is_dir() and d.name.startswith("@")])
    if not available:
        print(Colors.yellow("  No mods found with @ prefix"))
        print()
        print(Colors.red(f"Please upload your mod to {mods_dir} first"))
        return

    for i, mod in enumerate(available, 1):
        print(f"  {i}. {Colors.yellow(mod.name)}")

    print()
    selection = prompt_input("Select a mod to install (or 'q' to quit):")

    if selection.lower() == "q":
        return

    try:
        idx = int(selection) - 1
        if idx < 0 or idx >= len(available):
            raise ValueError
    except ValueError:
        print(Colors.red("Invalid selection"))
        return

    mod_path = available[idx]
    mod_name = mod_path.name

    print()
    banner(f"Installing: {mod_name}")

    # Validate mod structure
    print(Colors.blue("Validating mod structure..."))
    warnings = []

    has_addons = (mod_path / "addons").is_dir() or (mod_path / "Addons").is_dir()
    if not has_addons:
        warnings.append("Warning: No 'addons' folder found")

    pbo_count = len(list(mod_path.rglob("*.pbo")))
    if pbo_count == 0:
        warnings.append("Warning: No .pbo files found")

    if not (mod_path / "mod.cpp").exists():
        print(Colors.yellow("  Note: No mod.cpp found (optional)"))

    if warnings:
        print()
        for w in warnings:
            print(Colors.yellow(f"  {w}"))
        print()
        print(Colors.yellow("This mod may not be properly structured."))
        if not confirm("Continue anyway?", auto_yes=auto_yes):
            return
    else:
        print(Colors.green("✓ Mod structure validated"))
        print(f"  - Found addons folder")
        print(f"  - Found {pbo_count} .pbo file(s)")

    # Copy keys
    print()
    print(Colors.blue("Copying mod keys..."))
    copy_keys(mod_path, keys_dir)

    # Lowercase
    print()
    print(Colors.blue("Converting contents to lowercase..."))
    lowercase_contents(mod_path)
    print(Colors.green("✓ Contents converted to lowercase"))

    # Update LGSM config
    print()
    print(Colors.blue("Updating server configuration..."))
    if lgsm_path.exists():
        add_mod_to_config(lgsm_path, mod_name)
    else:
        print(Colors.yellow(f"Warning: LinuxGSM config not found at {config.lgsm_config}"))

    # Summary
    print()
    banner("Installation Complete!")
    print(Colors.blue("Mod Details:"))
    print(f"  Mod Name: {Colors.yellow(mod_name)}")
    print(f"  Location: {Colors.yellow(str(mod_path))}")
    print()
    display_current_mods(config)

    if not auto_yes:
        while True:
            ans = prompt_input("Would you like to install another mod? (y/n):")
            if ans.lower() in ("y", "yes"):
                _do_manual_install(config, auto_yes)
                return
            elif ans.lower() in ("n", "no"):
                print(Colors.green("All done! Don't forget to restart your server."))
                return
            else:
                print(Colors.red("Please answer y or n."))


def cmd_batch_install(args, config: Config):
    """Batch install from mod list file."""
    banner(f"DayZ Batch Mod Installer v{TEMS_VERSION}")

    auto_yes = getattr(args, "yes", False)

    if not Path(config.steamcmd_path).exists():
        print(Colors.red(f"Error: SteamCMD not found at {config.steamcmd_path}"))
        return

    mods_dir = Path(config.server_mods_dir)
    mods_dir.mkdir(parents=True, exist_ok=True)

    mod_list_file = Path(args.file)
    if not mod_list_file.exists():
        print(Colors.red(f"Error: Mod list file not found: {mod_list_file}"))
        return

    # Parse mod list
    pattern = re.compile(
        r'^(.+?)\s*-\s*https://steamcommunity\.com/sharedfiles/filedetails/\?id=(\d+)'
    )
    mods_to_install = []  # list of (name, workshop_id)

    for line in mod_list_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = pattern.match(line)
        if m:
            name = ensure_at_prefix(m.group(1).strip().replace(" ", ""))
            mods_to_install.append((name, m.group(2)))

    total = len(mods_to_install)
    print(Colors.cyan(f"Found {total} mod(s) in list"))
    print()

    if not confirm(f"This will download and install {total} mods. Continue?", auto_yes=auto_yes):
        print(Colors.yellow("Cancelled"))
        return

    print()

    # Validate workshop IDs
    print(Colors.blue("Validating Workshop IDs..."))
    invalid = []
    for name, wid in mods_to_install:
        status = validate_workshop_id_online(wid)
        if status == "ok":
            print(f"  {Colors.green('✓')} {name} (ID: {wid})")
        elif status == "not_found":
            print(f"  {Colors.red('✗')} {name} (ID: {wid}) - NOT FOUND")
            invalid.append(name)
        else:
            print(f"  {Colors.yellow('?')} {name} (ID: {wid}) - Could not validate")

    if invalid:
        print()
        print(Colors.red("The following mods have invalid Workshop IDs:"))
        for mod in invalid:
            print(f"  {Colors.red('✗')} {mod}")
        print()
        if not confirm("Continue anyway?", auto_yes=auto_yes):
            return

    print()

    # Build SteamCMD script for batch download
    script_lines = [f"login {config.steam_user} {config.steam_pass}"]
    for _name, wid in mods_to_install:
        script_lines.append(f"workshop_download_item {config.dayz_app_id} {wid}")
    script_lines.append("quit")

    print(Colors.blue("Downloading all mods in a single SteamCMD session..."))
    print(Colors.yellow("This may take a while..."))
    print()

    dl_result = run_steamcmd_script(config, script_lines)
    if dl_result != 0:
        print(Colors.red("SteamCMD download session failed"))
        print(Colors.yellow("Some or all mods may not have downloaded. Continuing with installation..."))
        print()

    # Process each mod
    successful = []
    failed = []
    keys_dir = Path(config.keys_dir)
    keys_dir.mkdir(parents=True, exist_ok=True)
    lgsm_path = Path(config.lgsm_config)

    for idx, (mod_name, wid) in enumerate(mods_to_install, 1):
        print(Colors.green("========================================"))
        print(Colors.green(f"[{idx}/{total}] Processing: {mod_name}"))
        print(Colors.green(f"Workshop ID: {wid}"))
        print(Colors.green("========================================"))
        print()

        workshop_path = Path(config.workshop_dir) / wid
        dest_path = mods_dir / mod_name

        if not workshop_path.is_dir():
            print(Colors.red(f"✗ Workshop files not found for {mod_name}"))
            failed.append(f"{mod_name} (ID: {wid})")
            print()
            continue

        # Copy files
        print(Colors.blue("Copying mod files..."))
        if dest_path.exists():
            print(Colors.yellow("Removing old version..."))
            shutil.rmtree(dest_path)
        try:
            shutil.copytree(str(workshop_path), str(dest_path))
            print(Colors.green("✓ Files copied"))
        except OSError:
            print(Colors.red(f"✗ Failed to copy files for {mod_name}"))
            failed.append(f"{mod_name} (ID: {wid})")
            print()
            continue

        # Copy keys
        print(Colors.blue("Copying mod keys..."))
        copy_keys(dest_path, keys_dir)

        # Lowercase
        print(Colors.blue("Converting contents to lowercase..."))
        lowercase_contents(dest_path)
        print(Colors.green("✓ Contents converted to lowercase"))

        # Clean up workshop files
        print(Colors.blue("Cleaning up Workshop files..."))
        try:
            shutil.rmtree(workshop_path)
            print(Colors.green("✓ Workshop files cleaned up"))
        except OSError:
            print(Colors.yellow("Warning: Could not clean up Workshop files"))

        # Save mapping
        print(Colors.blue("Saving mod mapping..."))
        write_mod_mapping(Path(config.mod_mapping_file), wid, mod_name)
        print(Colors.green("✓ Mod mapping saved"))

        # Update config
        print(Colors.blue("Updating server configuration..."))
        if lgsm_path.exists():
            add_mod_to_config(lgsm_path, mod_name)

        print(Colors.green(f"✓ {mod_name} installed successfully!"))
        successful.append(mod_name)
        print()

    # Summary
    print()
    banner("Installation Complete!")
    print(Colors.cyan("Summary:"))
    print(f"  Total mods: {Colors.yellow(str(total))}")
    print(f"  Successful: {Colors.green(str(len(successful)))}")
    print(f"  Failed: {Colors.red(str(len(failed)))}")
    print()

    if failed:
        print(Colors.red("Failed mods:"))
        for mod in failed:
            print(f"  {Colors.red('✗')} {mod}")
        print()

    print(Colors.yellow("Current mod load order:"))
    display_current_mods(config)

    print(Colors.cyan("Next steps:"))
    print(f"  1. Use {Colors.yellow('tems.py reorder')} to adjust load order if needed")
    print(f"  2. Restart your server: {Colors.yellow('./dayzserver restart')}")
    print()


def cmd_update(args, config: Config):
    """Update all mapped mods."""
    banner(f"DayZ Mod Auto-Updater v{TEMS_VERSION}")

    auto_yes = getattr(args, "yes", False)

    if not Path(config.steamcmd_path).exists():
        print(Colors.red(f"Error: SteamCMD not found at {config.steamcmd_path}"))
        return

    mapping_file = Path(config.mod_mapping_file)

    if not mapping_file.exists() or mapping_file.stat().st_size == 0:
        print(Colors.yellow("No mod mapping file found. Creating one now..."))
        print()
        print(Colors.cyan("This file will track which Workshop IDs correspond to which mod directories."))
        print()

        mods_dir = Path(config.server_mods_dir)
        if mods_dir.is_dir():
            for mod_dir in sorted(mods_dir.iterdir()):
                if mod_dir.is_dir() and mod_dir.name.startswith("@"):
                    print(Colors.yellow(f"Found mod: {mod_dir.name}"))
                    wid = prompt_input(f"Enter Workshop ID for {mod_dir.name} (or press Enter to skip):")
                    if wid and validate_workshop_id(wid):
                        write_mod_mapping(mapping_file, wid, mod_dir.name)
                        print(Colors.green(f"✓ Mapped {mod_dir.name} to {wid}"))
                    print()

        if not mapping_file.exists() or mapping_file.stat().st_size == 0:
            print(Colors.red("No mods mapped. Run the install command first."))
            return

    mapping = read_mod_mapping(mapping_file)
    mod_count = len(mapping)

    print(Colors.blue("Reading mod mappings..."))
    print()
    print(Colors.cyan(f"Found {mod_count} mod(s) to update"))
    print()

    if not confirm(f"Update {mod_count} mods?", default=True, auto_yes=auto_yes):
        print(Colors.yellow("Cancelled"))
        return

    # Build SteamCMD script
    script_lines = [f"login {config.steam_user} {config.steam_pass}"]
    for wid in mapping:
        script_lines.append(f"workshop_download_item {config.dayz_app_id} {wid} validate")
    script_lines.append("quit")

    print(Colors.blue("Downloading all mod updates in a single SteamCMD session..."))
    print(Colors.yellow("This may take a while..."))
    print()

    dl_result = run_steamcmd_script(config, script_lines)
    if dl_result != 0:
        print(Colors.red("SteamCMD download session failed"))
        print(Colors.yellow("Some or all mods may not have updated. Continuing with processing..."))
        print()

    # Process each mod
    keys_dir = Path(config.keys_dir)
    keys_dir.mkdir(parents=True, exist_ok=True)
    mods_dir = Path(config.server_mods_dir)

    for idx, (wid, mod_name) in enumerate(mapping.items(), 1):
        print(Colors.green("========================================"))
        print(Colors.green(f"[{idx}/{mod_count}] Processing: {mod_name}"))
        print(Colors.green(f"Workshop ID: {wid}"))
        print(Colors.green("========================================"))
        print()

        workshop_path = Path(config.workshop_dir) / wid
        dest_path = mods_dir / mod_name

        if not workshop_path.is_dir():
            print(Colors.red(f"✗ Workshop files not found for {mod_name}"))
            print()
            continue

        # Remove old version and copy
        if dest_path.exists():
            print(Colors.blue("Removing old version..."))
            shutil.rmtree(dest_path)

        print(Colors.blue("Copying updated files..."))
        try:
            shutil.copytree(str(workshop_path), str(dest_path))
            print(Colors.green("✓ Files copied"))
        except OSError:
            print(Colors.red(f"✗ Failed to copy files for {mod_name}"))
            print()
            continue

        # Copy keys
        print(Colors.blue("Updating keys..."))
        copy_keys(dest_path, keys_dir)

        # Lowercase
        print(Colors.blue("Converting contents to lowercase..."))
        lowercase_contents(dest_path)
        print(Colors.green("✓ Contents converted to lowercase"))

        # Clean up workshop files
        print(Colors.blue("Cleaning up Workshop files..."))
        try:
            shutil.rmtree(workshop_path)
            print(Colors.green("✓ Workshop files cleaned up"))
        except OSError:
            print(Colors.yellow("Warning: Could not clean up Workshop files"))

        print(Colors.green(f"✓ {mod_name} updated successfully!"))
        print()

    banner("All Mods Updated!")
    print(Colors.cyan(f"Updated {mod_count} mod(s)"))
    print()
    print(Colors.yellow("Don't forget to restart your server!"))
    print()


def cmd_reorder(args, config: Config):
    """Interactive load order manager."""
    banner(f"DayZ Mod Load Order Manager v{TEMS_VERSION}")

    lgsm_path = Path(config.lgsm_config)
    if not lgsm_path.exists():
        print(Colors.red(f"Error: Config file not found at {config.lgsm_config}"))
        return

    mods = read_lgsm_mods(lgsm_path)
    if not mods:
        print(Colors.yellow("No mods configured yet"))
        return

    print(Colors.cyan("Load Order Best Practices:"))
    print(f"{Colors.yellow('1.')} Map mods (like @Banov) should be FIRST")
    print(f"{Colors.yellow('2.')} Framework mods (@CF, @DabsFramework) load early")
    print(f"{Colors.yellow('3.')} @DayZ-Expansion-Core before other Expansion mods")
    print(f"{Colors.yellow('4.')} Dependency mods before mods that require them")
    print()

    def display():
        print(Colors.blue("Current Load Order:"))
        for i, mod in enumerate(mods, 1):
            print(f"  {i}. {Colors.yellow(mod)}")
        print()

    while True:
        display()

        print(Colors.yellow("Options:"))
        print("  1. Move a mod up (load earlier)")
        print("  2. Move a mod down (load later)")
        print("  3. Move a mod to specific position")
        print("  4. Save and exit")
        print("  5. Cancel (don't save)")
        print()
        choice = prompt_input("Choose option (1-5):")

        if choice == "1":
            num = prompt_input("Enter the number of the mod to move UP:")
            try:
                idx = int(num) - 1
                if idx < 0 or idx >= len(mods):
                    raise ValueError
            except ValueError:
                print(Colors.red("Invalid selection"))
                print()
                continue

            if idx == 0:
                print(Colors.yellow("Already at the top!"))
                print()
                continue

            mods[idx], mods[idx - 1] = mods[idx - 1], mods[idx]
            print(Colors.green(f"✓ Moved {mods[idx - 1]} up"))
            print()

        elif choice == "2":
            num = prompt_input("Enter the number of the mod to move DOWN:")
            try:
                idx = int(num) - 1
                if idx < 0 or idx >= len(mods):
                    raise ValueError
            except ValueError:
                print(Colors.red("Invalid selection"))
                print()
                continue

            if idx == len(mods) - 1:
                print(Colors.yellow("Already at the bottom!"))
                print()
                continue

            mods[idx], mods[idx + 1] = mods[idx + 1], mods[idx]
            print(Colors.green(f"✓ Moved {mods[idx + 1]} down"))
            print()

        elif choice == "3":
            num = prompt_input("Enter the number of the mod to move:")
            try:
                old_idx = int(num) - 1
                if old_idx < 0 or old_idx >= len(mods):
                    raise ValueError
            except ValueError:
                print(Colors.red("Invalid selection"))
                print()
                continue

            new_num = prompt_input(f"Enter the new position (1-{len(mods)}):")
            try:
                new_idx = int(new_num) - 1
                if new_idx < 0 or new_idx >= len(mods):
                    raise ValueError
            except ValueError:
                print(Colors.red("Invalid position"))
                print()
                continue

            if old_idx == new_idx:
                print(Colors.yellow("Same position!"))
                print()
                continue

            mod = mods.pop(old_idx)
            mods.insert(new_idx, mod)
            print(Colors.green(f"✓ Moved {mod} to position {new_idx + 1}"))
            print()

        elif choice == "4":
            write_lgsm_mods(lgsm_path, mods)
            print()
            banner("Load order saved!")
            print(Colors.blue("Final Load Order:"))
            for i, mod in enumerate(mods, 1):
                print(f"  {i}. {Colors.yellow(mod)}")
            print()
            print(Colors.cyan("Remember to restart your server for changes to take effect!"))
            return

        elif choice == "5":
            print()
            print(Colors.yellow("Cancelled - no changes saved"))
            return

        else:
            print(Colors.red("Invalid option"))
            print()


def cmd_export(args, config: Config):
    """Export mod list to file."""
    banner(f"Export Current Mod List v{TEMS_VERSION}")

    mapping_file = Path(config.mod_mapping_file)
    if not mapping_file.exists():
        print(Colors.red(f"Error: No mod mapping file found at {mapping_file}"))
        print(Colors.yellow("You need to have mods installed via the install command first"))
        return

    output = getattr(args, "output", None)
    if not output:
        output = prompt_input("Enter output filename (or press Enter for 'my_mod_list.txt'):")
        if not output:
            output = "my_mod_list.txt"

    if not output.endswith(".txt"):
        output += ".txt"

    print()
    print(Colors.blue(f"Exporting mod list to: {output}"))
    print()

    mapping = read_mod_mapping(mapping_file)

    with open(output, "w") as f:
        f.write("# DayZ Server Mod List\n")
        f.write("# Format: ModName - https://steamcommunity.com/sharedfiles/filedetails/?id=WORKSHOP_ID\n")
        f.write("# Lines starting with # are ignored\n")
        f.write("# Generated by tems.py\n")
        f.write("\n")
        for wid, mod_name in mapping.items():
            display_name = mod_name.lstrip("@")
            f.write(f"{display_name} - https://steamcommunity.com/sharedfiles/filedetails/?id={wid}\n")

    mod_count = len(mapping)
    print(Colors.green(f"✓ Exported {mod_count} mod(s)"))
    print()
    print(f"{Colors.cyan('Output file:')} {Colors.yellow(output)}")
    print()
    print(Colors.blue("You can now use this file with:"))
    print(f"  {Colors.yellow(f'tems.py batch-install {output}')}")
    print()
    print(Colors.cyan("Tip: Edit the file to:"))
    print("  - Remove mods you don't want")
    print("  - Add new mods")
    print("  - Change the order (top = loads first)")
    print()


def cmd_cleanup(args, config: Config):
    """Remove mods from config."""
    banner(f"DayZ Mods Config Cleanup v{TEMS_VERSION}")

    lgsm_path = Path(config.lgsm_config)
    if not lgsm_path.exists():
        print(Colors.red(f"Error: Config file not found at {config.lgsm_config}"))
        return

    mods = read_lgsm_mods(lgsm_path)
    if not mods:
        print(Colors.yellow("No mods configured yet"))
        return

    print(Colors.blue("Current mods in config:"))
    print()
    for i, mod in enumerate(mods, 1):
        print(f"  {i}. {Colors.yellow(mod)}")

    print()
    print(Colors.yellow("Options:"))
    print("  1. Remove a specific mod")
    print("  2. Clear all mods")
    print("  3. Cancel")
    print()
    choice = prompt_input("Choose option (1-3):")

    if choice == "1":
        num = prompt_input("Enter the number of the mod to remove:")
        try:
            idx = int(num) - 1
            if idx < 0 or idx >= len(mods):
                raise ValueError
        except ValueError:
            print(Colors.red("Invalid selection"))
            return

        removed = mods.pop(idx)
        write_lgsm_mods(lgsm_path, mods)
        print()
        print(Colors.green(f"✓ Removed {removed}"))
        print()
        if mods:
            print(Colors.blue("Updated mods list:"))
            for i, mod in enumerate(mods, 1):
                print(f"  {i}. {Colors.yellow(mod)}")
        else:
            print(Colors.yellow("All mods removed"))

    elif choice == "2":
        if confirm("Are you sure you want to remove ALL mods?"):
            write_lgsm_mods(lgsm_path, [])
            print()
            print(Colors.green("✓ Cleared all mods from config"))
        else:
            print(Colors.yellow("Cancelled"))

    elif choice == "3":
        return

    else:
        print(Colors.red("Invalid option"))


BACKUP_SCOPES = {
    "1": (["world"], "world"),
    "2": (["mods"], "mods"),
    "3": (["configs"], "configs"),
    "4": (["world", "configs"], "world-configs"),
    "5": (["world", "mods", "configs"], "everything"),
}


def cmd_backup(args, config: Config):
    """Back up server data to local disk and/or rclone remote."""
    banner(f"TEMS Backup v{TEMS_VERSION}")

    auto_yes = getattr(args, "yes", False)
    scope_arg = getattr(args, "scope", None)
    dest_arg = getattr(args, "dest", None)

    # ── Determine scope ──────────────────────────────────────────────────
    if scope_arg:
        # CLI flag: --scope world,configs
        scopes = [s.strip() for s in scope_arg.split(",")]
        if "full" in scopes:
            run_lgsm_backup(config)
            return
        label = "-".join(scopes)
    elif auto_yes and config.backup_default_scope:
        scopes = [s.strip() for s in config.backup_default_scope.split(",")]
        if "full" in scopes:
            run_lgsm_backup(config)
            return
        label = "-".join(scopes)
    else:
        # Interactive scope selection
        print(Colors.cyan("What would you like to back up?"))
        print(f"  1. {Colors.yellow('World data')}      (mpmissions/persistence)")
        print(f"  2. {Colors.yellow('Mods')}            (serverfiles/mods)")
        print(f"  3. {Colors.yellow('Configs')}         (tems.yaml, LGSM config, mod mapping, keys)")
        print(f"  4. {Colors.yellow('World + Configs')} (recommended for daily backup)")
        print(f"  5. {Colors.yellow('Everything')}      (world + mods + configs)")
        print(f"  6. {Colors.yellow('Full server')}     (LinuxGSM native backup)")
        print()
        choice = prompt_input("Choose scope (1-6):")

        if choice == "6":
            run_lgsm_backup(config)
            return

        if choice not in BACKUP_SCOPES:
            print(Colors.red("Invalid option"))
            return
        scopes, label = BACKUP_SCOPES[choice]

    # ── Gather source paths ──────────────────────────────────────────────
    source_paths = gather_backup_paths(config, scopes)
    if not source_paths:
        print(Colors.red("Error: No files found to back up for the selected scope"))
        return

    print()
    print(Colors.blue(f"Scope: {', '.join(scopes)}"))
    print(Colors.blue(f"Sources ({len(source_paths)}):"))
    for p in source_paths:
        print(f"  {Colors.yellow(str(p))}")
    print()

    # ── Determine destination ────────────────────────────────────────────
    rclone_remote = config.backup_rclone_remote
    backup_dir = Path(config.backup_dir)

    if dest_arg:
        dests = [d.strip() for d in dest_arg.split(",")]
    elif auto_yes and config.backup_default_dest:
        dests = [d.strip() for d in config.backup_default_dest.split(",")]
    else:
        # Interactive destination selection
        print(Colors.cyan("Where should the backup go?"))
        print(f"  1. {Colors.yellow('Local disk')}     ({backup_dir})")
        if rclone_remote:
            print(f"  2. {Colors.yellow('rclone remote')} ({rclone_remote})")
            print(f"  3. {Colors.yellow('Both')}          (local + rclone)")
            print()
            dest_choice = prompt_input("Choose destination (1-3):")
            if dest_choice == "1":
                dests = ["local"]
            elif dest_choice == "2":
                dests = ["rclone"]
            elif dest_choice == "3":
                dests = ["local", "rclone"]
            else:
                print(Colors.red("Invalid option"))
                return
        else:
            print(f"  2. {Colors.yellow('rclone remote')} (not configured)")
            print()
            print(Colors.yellow("Tip: Set backup_rclone_remote in tems.yaml for cloud backups"))
            print()
            dest_choice = prompt_input("Choose destination (1-2):")
            if dest_choice == "1":
                dests = ["local"]
            elif dest_choice == "2":
                remote = prompt_input("Enter rclone remote (e.g., gdrive:dayz-backups):")
                if not remote:
                    print(Colors.red("No remote specified"))
                    return
                rclone_remote = remote
                dests = ["rclone"]
            else:
                print(Colors.red("Invalid option"))
                return

    # ── Confirmation ─────────────────────────────────────────────────────
    if not auto_yes:
        print()
        if not confirm("Proceed with backup?", default=True):
            print("Backup cancelled.")
            return

    print()

    # ── Check disk space (local) ─────────────────────────────────────────
    if "local" in dests:
        backup_dir.mkdir(parents=True, exist_ok=True)
        check_disk_space(str(backup_dir))

    # ── Create archive ───────────────────────────────────────────────────
    archive = create_backup_archive(source_paths, backup_dir, label)

    # ── Upload to rclone if requested ────────────────────────────────────
    if "rclone" in dests:
        remote = rclone_remote
        if not remote:
            print(Colors.red("Error: No rclone remote configured"))
            print(Colors.yellow("Set backup_rclone_remote in tems.yaml"))
        else:
            print()
            upload_rclone(archive, remote)

    # ── Rotate old local backups ─────────────────────────────────────────
    keep = int(config.backup_keep)
    if "local" in dests and keep > 0:
        print()
        rotate_backups(backup_dir, keep)

    # ── Clean up local archive if only uploading to rclone ───────────────
    if "rclone" in dests and "local" not in dests:
        archive.unlink(missing_ok=True)
        print(Colors.blue("Local archive removed (rclone-only mode)"))

    print()
    print(Colors.green("✓ Backup complete"))


# ─── XML Merger (integrated from DMXM) ──────────────────────────────────────

class XMLMerger:
    """Merges mod types.xml, events.xml, and spawnabletypes.xml into server
    mission files. Integrated from the standalone DMXM tool."""

    def __init__(self, config: Config):
        self.tems_config = config
        self.config_file = Path(__file__).resolve().parent / "merge_config.json"
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Load or create merge_config.json."""
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                return json.load(f)

        # Build defaults from TEMS config
        mods_dir = self.tems_config.server_mods_dir
        mission_dir = self.tems_config.mission_dir
        mission_name = Path(mission_dir).name
        mpmissions_base = str(Path(mission_dir).parent)

        default_config = {
            "backup_enabled": True,
            "backup_folder": str(Path(__file__).resolve().parent / "xml_backups"),
            "active_mission": mission_name,
            "missions": {
                mission_name: {
                    "types": str(Path(mission_dir) / "db" / "types.xml"),
                    "events": str(Path(mission_dir) / "cfgeventspawns.xml"),
                    "spawnabletypes": str(Path(mission_dir) / "db" / "spawnabletypes.xml"),
                }
            },
            "mod_search_paths": [
                mods_dir,
            ],
            "merge_rules": {
                "skip_vanilla_duplicates": True,
                "overwrite_existing": False,
                "preserve_comments": True,
            },
        }
        self._save_config(default_config)
        return default_config

    def _save_config(self, cfg: dict | None = None):
        """Save merge configuration to file."""
        if cfg is None:
            cfg = self.config
        with open(self.config_file, "w") as f:
            json.dump(cfg, f, indent=4)
        print(Colors.green(f"  ✓ Merge config saved to {self.config_file}"))

    # ── Mission helpers ──────────────────────────────────────────────────

    def get_xml_paths(self) -> dict:
        active = self.config.get("active_mission", "")
        return self.config["missions"].get(active, {})

    def list_missions(self) -> list[str]:
        return list(self.config["missions"].keys())

    def set_active_mission(self, name: str):
        if name in self.config["missions"]:
            self.config["active_mission"] = name
            self._save_config()
            print(Colors.green(f"  ✓ Active mission set to: {name}"))
        else:
            print(Colors.red(f"  Mission '{name}' not found in configuration"))

    def scan_mpmissions_folders(self) -> list[dict]:
        """Scan for mission folders in common locations."""
        search_paths = [
            str(Path(self.tems_config.mission_dir).parent),
            os.path.expanduser("~/serverfiles/mpmissions"),
        ]
        # Deduplicate
        search_paths = list(dict.fromkeys(search_paths))

        found = []
        for base_path in search_paths:
            if not os.path.isdir(base_path):
                continue
            print(f"  Scanning: {Colors.blue(base_path)}")
            for item in os.listdir(base_path):
                mission_path = os.path.join(base_path, item)
                if not os.path.isdir(mission_path):
                    continue
                db_path = os.path.join(mission_path, "db")
                events_file = os.path.join(mission_path, "cfgeventspawns.xml")
                if os.path.exists(db_path) or os.path.exists(events_file):
                    info = {
                        "name": item,
                        "path": mission_path,
                        "types": os.path.join(mission_path, "db", "types.xml"),
                        "events": events_file,
                        "spawnabletypes": os.path.join(mission_path, "db", "spawnabletypes.xml"),
                    }
                    if (os.path.exists(info["types"]) or
                            os.path.exists(info["events"]) or
                            os.path.exists(info["spawnabletypes"])):
                        found.append(info)
                        print(f"    {Colors.green('✓')} Found: {item}")
        return found

    def auto_configure_missions(self):
        """Auto-detect and configure missions."""
        banner("Auto-detecting Mission Folders")
        found = self.scan_mpmissions_folders()

        if not found:
            print(Colors.red("  No mission folders found."))
            print(Colors.yellow("  Make sure you have types.xml or cfgeventspawns.xml in your mission folder."))
            return False

        print()
        print(Colors.cyan(f"Found {len(found)} mission folder(s):"))
        for i, m in enumerate(found, 1):
            tag = Colors.yellow(" (already configured)") if m["name"] in self.config["missions"] else Colors.green(" (new)")
            print(f"  {i}. {Colors.yellow(m['name'])}{tag}")
            if os.path.exists(m["types"]):
                print(f"     {Colors.green('✓')} types.xml")
            if os.path.exists(m["events"]):
                print(f"     {Colors.green('✓')} events.xml")
            if os.path.exists(m["spawnabletypes"]):
                print(f"     {Colors.green('✓')} spawnabletypes.xml")

        print()
        print(Colors.yellow("Options:"))
        print("  1. Add all detected missions")
        print("  2. Select specific missions to add")
        print("  3. Cancel")
        choice = prompt_input("Select option:")

        if choice == "1":
            added = 0
            for m in found:
                if m["name"] not in self.config["missions"]:
                    self.config["missions"][m["name"]] = {
                        "types": m["types"],
                        "events": m["events"],
                        "spawnabletypes": m["spawnabletypes"],
                    }
                    added += 1
                    print(f"  {Colors.green('+')} Added: {m['name']}")
            if added:
                if not self.config.get("active_mission") or self.config["active_mission"] not in self.config["missions"]:
                    self.config["active_mission"] = found[0]["name"]
                self._save_config()
                print(Colors.green(f"\n  ✓ Added {added} mission(s)"))
            else:
                print(Colors.yellow("\n  All missions already configured"))
            return True

        elif choice == "2":
            selected = prompt_input("Enter numbers (comma-separated, e.g. 1,3):")
            try:
                indices = [int(x.strip()) - 1 for x in selected.split(",")]
                added = 0
                for idx in indices:
                    if 0 <= idx < len(found):
                        m = found[idx]
                        if m["name"] not in self.config["missions"]:
                            self.config["missions"][m["name"]] = {
                                "types": m["types"],
                                "events": m["events"],
                                "spawnabletypes": m["spawnabletypes"],
                            }
                            added += 1
                            print(f"  {Colors.green('+')} Added: {m['name']}")
                if added:
                    if not self.config.get("active_mission") or self.config["active_mission"] not in self.config["missions"]:
                        self.config["active_mission"] = found[indices[0]]["name"]
                    self._save_config()
                    print(Colors.green(f"\n  ✓ Added {added} mission(s)"))
                return True
            except (ValueError, IndexError):
                print(Colors.red("  Invalid selection"))
                return False

        return False

    # ── XML parsing / merging ────────────────────────────────────────────

    def backup_xml(self, xml_path: str):
        """Create a backup of an XML file before modifying it."""
        if not self.config["backup_enabled"]:
            return
        if not os.path.exists(xml_path):
            return
        backup_dir = self.config["backup_folder"]
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(xml_path)
        backup_path = os.path.join(backup_dir, f"{filename}.{timestamp}.bak")
        shutil.copy2(xml_path, backup_path)
        print(f"    {Colors.green('✓')} Backup: {backup_path}")

    def _parse_xml(self, path: str) -> ET.Element | None:
        try:
            return ET.parse(path).getroot()
        except ET.ParseError as e:
            print(Colors.yellow(f"    Warning: Could not parse {path}: {e}"))
            return None
        except Exception as e:
            print(Colors.yellow(f"    Warning: Error reading {path}: {e}"))
            return None

    def _save_xml(self, root: ET.Element, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tree = ET.ElementTree(root)
        ET.indent(tree, space="    ")
        tree.write(path, encoding="utf-8", xml_declaration=True)

    def find_mod_xml_files(self, mod_path: str) -> dict[str, list[str]]:
        """Find types/events/spawnabletypes XML files inside a mod folder."""
        found: dict[str, list[str]] = {"types": [], "events": [], "spawnabletypes": []}
        try:
            all_xml = list(Path(mod_path).rglob("*.xml"))
        except Exception:
            return found

        for xml_file in all_xml:
            try:
                if xml_file.stat().st_size > 50 * 1024 * 1024:
                    continue
                with open(xml_file, "r", encoding="utf-8", errors="ignore") as f:
                    sample = ""
                    for i, line in enumerate(f):
                        sample += line
                        if i > 20:
                            break
                sample_lower = sample.lower()
                if "<types>" in sample_lower or "<types " in sample_lower or ("<type " in sample_lower and "name=" in sample_lower):
                    if str(xml_file) not in found["types"]:
                        found["types"].append(str(xml_file))
                elif "<eventposdef" in sample_lower or ("<event " in sample_lower and "name=" in sample_lower):
                    if str(xml_file) not in found["events"]:
                        found["events"].append(str(xml_file))
                elif "<spawnabletypes" in sample_lower:
                    if str(xml_file) not in found["spawnabletypes"]:
                        found["spawnabletypes"].append(str(xml_file))
            except Exception:
                continue
        return found

    def scan_for_mods(self) -> list[str]:
        """Scan configured paths for mod folders."""
        mods_found = []
        for search_path in self.config["mod_search_paths"]:
            search_path = os.path.expanduser(search_path)
            if "*" in search_path:
                base = search_path.split("*")[0]
                if os.path.exists(base):
                    try:
                        for item in Path(base).parent.glob(os.path.basename(search_path)):
                            if item.is_dir():
                                mods_found.append(str(item))
                    except Exception:
                        pass
            elif os.path.isdir(search_path):
                try:
                    for item in os.listdir(search_path):
                        item_path = os.path.join(search_path, item)
                        if os.path.isdir(item_path) and (item.startswith("@") or "mod" in item.lower()):
                            mods_found.append(item_path)
                except Exception:
                    pass
        return sorted(set(mods_found))

    def _merge_xml(self, server_path: str, mod_path: str, tag: str, root_tag: str) -> tuple[int, int, int]:
        """Generic merge: merge elements with `tag` from mod XML into server XML."""
        server_root = self._parse_xml(server_path)
        if server_root is None:
            server_root = ET.Element(root_tag)

        mod_root = self._parse_xml(mod_path)
        if mod_root is None:
            print(Colors.red(f"    Skipping: Could not read {mod_path}"))
            return 0, 0, 0

        existing = {elem.get("name"): elem for elem in server_root.findall(tag)}
        added = updated = skipped = 0
        overwrite = self.config["merge_rules"]["overwrite_existing"]

        for elem in mod_root.findall(tag):
            name = elem.get("name")
            if not name:
                continue
            if name in existing:
                if overwrite:
                    server_root.remove(existing[name])
                    server_root.append(elem)
                    updated += 1
                    print(f"      {Colors.blue('↻')} Updated: {name}")
                else:
                    skipped += 1
            else:
                server_root.append(elem)
                added += 1
                print(f"      {Colors.green('+')} Added: {name}")

        self._save_xml(server_root, server_path)
        return added, updated, skipped

    def merge_mod(self, mod_path: str):
        """Merge all XML files from one mod into server mission XMLs."""
        print()
        banner(f"Processing: {os.path.basename(mod_path)}")

        xml_files = self.find_mod_xml_files(mod_path)
        if not any(xml_files.values()):
            print(Colors.yellow("  No mergeable XML files found in this mod"))
            return

        server_paths = self.get_xml_paths()
        total_added = total_updated = total_skipped = 0

        # types.xml
        if xml_files["types"]:
            print(Colors.blue(f"  Found {len(xml_files['types'])} types.xml file(s)"))
            for mod_types in xml_files["types"]:
                print(f"    Merging: {mod_types}")
                srv = server_paths.get("types")
                if srv:
                    self.backup_xml(srv)
                    a, u, s = self._merge_xml(srv, mod_types, "type", "types")
                    total_added += a
                    total_updated += u
                    total_skipped += s
                else:
                    print(Colors.yellow("    Server types.xml path not configured"))

        # events.xml
        if xml_files["events"]:
            print(Colors.blue(f"  Found {len(xml_files['events'])} events.xml file(s)"))
            for mod_events in xml_files["events"]:
                print(f"    Merging: {mod_events}")
                srv = server_paths.get("events")
                if srv:
                    self.backup_xml(srv)
                    a, u, s = self._merge_xml(srv, mod_events, "event", "eventposdef")
                    total_added += a
                    total_updated += u
                    total_skipped += s
                else:
                    print(Colors.yellow("    Server events.xml path not configured"))

        # spawnabletypes.xml
        if xml_files["spawnabletypes"]:
            print(Colors.blue(f"  Found {len(xml_files['spawnabletypes'])} spawnabletypes.xml file(s)"))
            for mod_sp in xml_files["spawnabletypes"]:
                print(f"    Merging: {mod_sp}")
                srv = server_paths.get("spawnabletypes")
                if srv:
                    self.backup_xml(srv)
                    a, u, s = self._merge_xml(srv, mod_sp, "type", "spawnabletypes")
                    total_added += a
                    total_updated += u
                    total_skipped += s
                else:
                    print(Colors.yellow("    Server spawnabletypes.xml path not configured"))

        print()
        print(Colors.cyan(f"  Summary: {total_added} added, {total_updated} updated, {total_skipped} skipped"))


def cmd_xml_merge(args, config: Config):
    """Interactive XML merge menu (formerly DMXM)."""
    merger = XMLMerger(config)

    while True:
        banner(f"XML Merger v{TEMS_VERSION}")
        print(f"  Active mission: {Colors.yellow(merger.config.get('active_mission', 'Not set'))}")
        print()

        print(Colors.cyan("Options:"))
        print(f"  1. {Colors.yellow('Quick merge')}       - Auto-scan mods & merge all")
        print(f"  2. {Colors.yellow('Merge specific')}    - Merge a specific mod folder")
        print(f"  3. {Colors.yellow('List mods')}         - Show mods and their XML files")
        print(f"  4. {Colors.yellow('Switch mission')}    - Change active mission")
        print(f"  5. {Colors.yellow('Auto-detect')}       - Scan for new mission folders")
        print(f"  6. {Colors.yellow('Manage missions')}   - Add/remove/edit missions")
        print(f"  7. {Colors.yellow('Merge settings')}    - View/change merge rules")
        print(f"  8. {Colors.yellow('Back to main menu')}")
        print()
        choice = prompt_input("Choose option (1-8):")

        if choice == "1":
            _xml_quick_merge(merger)

        elif choice == "2":
            mod_path = prompt_input("Enter mod folder path:")
            if os.path.isdir(mod_path):
                merger.merge_mod(mod_path)
            else:
                print(Colors.red(f"  Path not found: {mod_path}"))

        elif choice == "3":
            _xml_list_mods(merger)

        elif choice == "4":
            _xml_switch_mission(merger)

        elif choice == "5":
            merger.auto_configure_missions()

        elif choice == "6":
            _xml_manage_missions(merger)

        elif choice == "7":
            _xml_merge_settings(merger)

        elif choice == "8":
            return

        else:
            print(Colors.red("Invalid option"))


def _xml_quick_merge(merger: XMLMerger):
    """Auto-scan and merge all mods into the active mission."""
    print()
    print(Colors.blue("Scanning for mods..."))
    mods = merger.scan_for_mods()

    if not mods:
        print(Colors.yellow("  No mods found. Check mod_search_paths in merge_config.json"))
        return

    print(Colors.cyan(f"\n  Found {len(mods)} mod folder(s):"))
    for i, mod in enumerate(mods, 1):
        print(f"    {i}. {Colors.yellow(os.path.basename(mod))}")

    print()
    if not confirm(f"Merge all {len(mods)} mods into {merger.config.get('active_mission')}?"):
        print(Colors.yellow("  Cancelled"))
        return

    for mod in mods:
        merger.merge_mod(mod)

    print()
    banner("All mods merged!")


def _xml_list_mods(merger: XMLMerger):
    """List available mods and their XML files."""
    print()
    print(Colors.blue("Scanning for mods..."))
    mods = merger.scan_for_mods()

    if not mods:
        print(Colors.yellow("  No mods found."))
        return

    print(Colors.cyan(f"\n  Found {len(mods)} mod folder(s):"))
    for i, mod in enumerate(mods, 1):
        print(f"    {i}. {Colors.yellow(os.path.basename(mod))}")
        xml_files = merger.find_mod_xml_files(mod)
        if xml_files["types"]:
            print(f"       {Colors.green('✓')} types.xml ({len(xml_files['types'])} file(s))")
        if xml_files["events"]:
            print(f"       {Colors.green('✓')} events.xml ({len(xml_files['events'])} file(s))")
        if xml_files["spawnabletypes"]:
            print(f"       {Colors.green('✓')} spawnabletypes.xml ({len(xml_files['spawnabletypes'])} file(s))")
        if not any(xml_files.values()):
            print(f"       {Colors.yellow('-')} No mergeable XML files")


def _xml_switch_mission(merger: XMLMerger):
    """Switch the active mission."""
    missions = merger.list_missions()
    if not missions:
        print(Colors.yellow("  No missions configured. Use auto-detect first."))
        return

    print()
    print(Colors.blue("Configured missions:"))
    for i, m in enumerate(missions, 1):
        tag = Colors.cyan(" <- ACTIVE") if m == merger.config.get("active_mission") else ""
        print(f"  {i}. {Colors.yellow(m)}{tag}")

    print()
    sel = prompt_input(f"Select mission (1-{len(missions)}):")
    try:
        idx = int(sel) - 1
        if 0 <= idx < len(missions):
            merger.set_active_mission(missions[idx])
        else:
            print(Colors.red("  Invalid selection"))
    except ValueError:
        print(Colors.red("  Invalid selection"))


def _xml_manage_missions(merger: XMLMerger):
    """Mission management submenu."""
    while True:
        print()
        banner("Mission Management")
        print(f"  Active: {Colors.yellow(merger.config.get('active_mission', 'Not set'))}")
        print()

        missions = merger.list_missions()
        print(Colors.blue("Configured missions:"))
        for i, m in enumerate(missions, 1):
            tag = Colors.cyan(" <- ACTIVE") if m == merger.config.get("active_mission") else ""
            print(f"  {i}. {Colors.yellow(m)}{tag}")
            paths = merger.config["missions"][m]
            print(f"     types: {paths.get('types', 'N/A')}")
            print(f"     events: {paths.get('events', 'N/A')}")

        print()
        print(Colors.yellow("Options:"))
        print("  1. Switch active mission")
        print("  2. Add new mission (auto-detect)")
        print("  3. Add new mission (manual)")
        print("  4. Remove mission")
        print("  5. Edit mission paths")
        print("  6. Back")
        print()
        choice = prompt_input("Choose option (1-6):")

        if choice == "1":
            _xml_switch_mission(merger)

        elif choice == "2":
            merger.auto_configure_missions()

        elif choice == "3":
            name = prompt_input("Enter mission name (e.g. dayzOffline.sakhal):")
            if not name:
                continue
            default_types = f"{Path(merger.tems_config.mission_dir).parent}/{name}/db/types.xml"
            default_events = f"{Path(merger.tems_config.mission_dir).parent}/{name}/cfgeventspawns.xml"
            default_sp = f"{Path(merger.tems_config.mission_dir).parent}/{name}/db/spawnabletypes.xml"

            types_p = prompt_input(f"types.xml path [{default_types}]:")
            events_p = prompt_input(f"events.xml path [{default_events}]:")
            sp_p = prompt_input(f"spawnabletypes.xml path [{default_sp}]:")

            merger.config["missions"][name] = {
                "types": types_p or default_types,
                "events": events_p or default_events,
                "spawnabletypes": sp_p or default_sp,
            }
            merger._save_config()
            print(Colors.green(f"  ✓ Added mission: {name}"))

        elif choice == "4":
            sel = prompt_input(f"Enter mission number to remove (1-{len(missions)}):")
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(missions):
                    name = missions[idx]
                    if confirm(f"Remove '{name}'?"):
                        del merger.config["missions"][name]
                        if merger.config.get("active_mission") == name:
                            remaining = merger.list_missions()
                            if remaining:
                                merger.config["active_mission"] = remaining[0]
                        merger._save_config()
                        print(Colors.green(f"  ✓ Removed: {name}"))
            except (ValueError, IndexError):
                print(Colors.red("  Invalid selection"))

        elif choice == "5":
            sel = prompt_input(f"Enter mission number to edit (1-{len(missions)}):")
            try:
                idx = int(sel) - 1
                if 0 <= idx < len(missions):
                    name = missions[idx]
                    current = merger.config["missions"][name]
                    print(Colors.blue(f"\n  Editing: {name}"))
                    print(Colors.yellow("  Leave blank to keep current value"))
                    tp = prompt_input(f"  types.xml [{current['types']}]:")
                    ep = prompt_input(f"  events.xml [{current['events']}]:")
                    sp = prompt_input(f"  spawnabletypes.xml [{current['spawnabletypes']}]:")
                    if tp:
                        current["types"] = tp
                    if ep:
                        current["events"] = ep
                    if sp:
                        current["spawnabletypes"] = sp
                    merger._save_config()
                    print(Colors.green("  ✓ Mission updated"))
            except (ValueError, IndexError):
                print(Colors.red("  Invalid selection"))

        elif choice == "6":
            return

        else:
            print(Colors.red("Invalid option"))


def _xml_merge_settings(merger: XMLMerger):
    """View/change merge rules."""
    print()
    banner("Merge Settings")
    rules = merger.config["merge_rules"]

    print(Colors.blue("Current settings:"))
    print(f"  Overwrite existing entries: {Colors.yellow(str(rules['overwrite_existing']))}")
    print(f"  Skip vanilla duplicates:   {Colors.yellow(str(rules['skip_vanilla_duplicates']))}")
    print(f"  Backup before merge:       {Colors.yellow(str(merger.config['backup_enabled']))}")
    print(f"  Backup folder:             {Colors.yellow(merger.config['backup_folder'])}")
    print()

    print(Colors.yellow("Options:"))
    print("  1. Toggle overwrite existing (currently: " +
          (Colors.green("ON") if rules["overwrite_existing"] else Colors.red("OFF")) + ")")
    print("  2. Toggle backups (currently: " +
          (Colors.green("ON") if merger.config["backup_enabled"] else Colors.red("OFF")) + ")")
    print("  3. Back")
    print()
    choice = prompt_input("Choose option (1-3):")

    if choice == "1":
        rules["overwrite_existing"] = not rules["overwrite_existing"]
        merger._save_config()
        state = Colors.green("ON") if rules["overwrite_existing"] else Colors.red("OFF")
        print(f"  Overwrite existing is now: {state}")
    elif choice == "2":
        merger.config["backup_enabled"] = not merger.config["backup_enabled"]
        merger._save_config()
        state = Colors.green("ON") if merger.config["backup_enabled"] else Colors.red("OFF")
        print(f"  Backups are now: {state}")


# ─── Main menu ───────────────────────────────────────────────────────────────

def cmd_menu(config: Config):
    """Interactive numbered menu — loops back after each action."""
    while True:
        print()
        banner(f"TEMS - Tsana Extended Management System v{TEMS_VERSION}")

        print(Colors.cyan("Choose a command:"))
        print()
        print(f"  1. {Colors.yellow('Install')}       - Download & install a single mod")
        print(f"  2. {Colors.yellow('Batch Install')} - Install multiple mods from a list file")
        print(f"  3. {Colors.yellow('Update')}        - Update all installed mods")
        print(f"  4. {Colors.yellow('Reorder')}       - Change mod load order")
        print(f"  5. {Colors.yellow('Export')}        - Export mod list to file")
        print(f"  6. {Colors.yellow('Cleanup')}       - Remove mods from config")
        print(f"  7. {Colors.yellow('Backup')}        - Back up server data")
        print(f"  8. {Colors.yellow('XML Merge')}     - Merge mod XMLs into mission files")
        print(f"  9. {Colors.yellow('Exit')}")
        print()

        choice = prompt_input("Choose option (1-9):")

        ns = argparse.Namespace(yes=False)

        if choice == "1":
            ns.workshop_id = None
            ns.name = None
            ns.manual = False
            cmd_install(ns, config)
            pause_before_menu()
        elif choice == "2":
            file_path = prompt_input("Enter path to mod list file:")
            if not file_path:
                print(Colors.red("No file specified"))
                continue
            ns.file = file_path
            cmd_batch_install(ns, config)
            pause_before_menu()
        elif choice == "3":
            cmd_update(ns, config)
            pause_before_menu()
        elif choice == "4":
            cmd_reorder(ns, config)
            pause_before_menu()
        elif choice == "5":
            ns.output = None
            cmd_export(ns, config)
            pause_before_menu()
        elif choice == "6":
            cmd_cleanup(ns, config)
            pause_before_menu()
        elif choice == "7":
            ns.scope = None
            ns.dest = None
            cmd_backup(ns, config)
            pause_before_menu()
        elif choice == "8":
            cmd_xml_merge(ns, config)
            # xml-merge has its own internal loop with "back to main menu"
        elif choice == "9":
            print(Colors.green("Goodbye!"))
            return
        else:
            print(Colors.red("Invalid option"))


# ─── Argument parsing ────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tems.py",
        description="TEMS - Tsana Extended Management System",
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to tems.yaml config file",
        default=None,
    )
    subparsers = parser.add_subparsers(dest="command")

    # install
    p_install = subparsers.add_parser("install", help="Install a single mod")
    p_install.add_argument("--workshop-id", "-w", dest="workshop_id", help="Steam Workshop ID")
    p_install.add_argument("--name", "-n", help="Mod name (e.g., @Banov)")
    p_install.add_argument("--manual", "-m", action="store_true", help="Manual install mode")
    p_install.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    # batch-install
    p_batch = subparsers.add_parser("batch-install", help="Batch install from mod list file")
    p_batch.add_argument("file", help="Path to mod list file")
    p_batch.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    # update
    p_update = subparsers.add_parser("update", help="Update all installed mods")
    p_update.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    # reorder
    subparsers.add_parser("reorder", help="Manage mod load order")

    # export
    p_export = subparsers.add_parser("export", help="Export mod list to file")
    p_export.add_argument("--output", "-o", help="Output filename")

    # cleanup
    subparsers.add_parser("cleanup", help="Remove mods from config")

    # backup
    p_backup = subparsers.add_parser("backup", help="Back up server data")
    p_backup.add_argument("--scope", "-s", help="Comma-separated: world,mods,configs,full")
    p_backup.add_argument("--dest", "-d", help="Comma-separated: local,rclone")
    p_backup.add_argument("--yes", "-y", action="store_true", help="Skip prompts (use config defaults)")

    # xml-merge
    subparsers.add_parser("xml-merge", help="Merge mod XML files into server mission")

    return parser


# ─── Entry point ─────────────────────────────────────────────────────────────

def main():
    ascii_banner()

    parser = build_parser()
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    config = Config(config_path)

    commands = {
        "install": cmd_install,
        "batch-install": cmd_batch_install,
        "update": cmd_update,
        "reorder": cmd_reorder,
        "export": cmd_export,
        "cleanup": cmd_cleanup,
        "backup": cmd_backup,
        "xml-merge": cmd_xml_merge,
    }

    if args.command is None:
        cmd_menu(config)
    elif args.command in commands:
        commands[args.command](args, config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
