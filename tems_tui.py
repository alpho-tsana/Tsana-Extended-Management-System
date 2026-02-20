#!/usr/bin/env python3
# =============================================================================
# TEMS TUI - Enhanced Terminal Interface for TEMS
# Version: 0.6
# Author: alpho-tsana (with assistance from Claude/Anthropic)
# License: GPL-3.0
#
# A rich, keyboard-only terminal interface. No external dependencies beyond
# what tems.py already requires. No mouse interaction.
#
# Usage:
#   python3 tems_tui.py                  → launch the enhanced interface
#   python3 tems_tui.py --config X.yaml  → use a custom config file
# =============================================================================

from __future__ import annotations

import argparse
import builtins
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ─── Import TEMS backend ────────────────────────────────────────────────────

from tems import (
    TEMS_VERSION,
    Config,
    Colors,
    banner,
    confirm,
    prompt_input,
    pause_before_menu,
    read_mod_mapping,
    read_lgsm_mods,
    get_mod_last_updated,
    get_mod_version,
    cmd_install,
    cmd_batch_install,
    cmd_update,
    cmd_reorder,
    cmd_export,
    cmd_cleanup,
    cmd_backup,
    cmd_restore,
    cmd_xml_merge,
    cmd_conflicts,
    cmd_deps,
    cmd_monitor,
    _format_size,
)


# ─── Typewriter engine ─────────────────────────────────────────────────────

# Speeds (seconds per character)
SPEED_FAST    = 0.003   # headers, rules, status — snappy but visible
SPEED_NORMAL  = 0.008   # menu items, settings lines
SPEED_SLOW    = 0.015   # important messages, goodbye

# Line delay (pause before each new line when printing backend output)
LINE_DELAY    = 0.015


def typewrite(text: str, speed: float = SPEED_NORMAL, end: str = "\n"):
    """Print text character by character with a typewriter effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        if char not in (" ", "\n"):
            time.sleep(speed)
    sys.stdout.write(end)
    sys.stdout.flush()


# Store reference to the real print
_real_print = builtins.print


def _patched_print(*args, **kwargs):
    """Drop-in replacement for print() that adds a small per-line delay.

    Monkey-patched onto builtins.print while backend cmd_* functions run,
    so their output streams to screen rather than appearing all at once.
    """
    _real_print(*args, **kwargs)
    file = kwargs.get("file", sys.stdout)
    if file is sys.stdout:
        time.sleep(LINE_DELAY)


def run_with_typewriter(func, *args, **kwargs):
    """Run a function with print() monkey-patched to add line delays."""
    builtins.print = _patched_print
    try:
        return func(*args, **kwargs)
    finally:
        builtins.print = _real_print


# ─── ANSI helpers ───────────────────────────────────────────────────────────

ORANGE = "\033[38;5;208m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
NC     = "\033[0m"


def clear():
    """Clear the terminal screen."""
    os.system("cls" if os.name == "nt" else "clear")


def orange(s: str) -> str:
    return f"{ORANGE}{s}{NC}"


def dim(s: str) -> str:
    return f"{DIM}{s}{NC}"


def bold(s: str) -> str:
    return f"{BOLD}{s}{NC}"


def rule(char: str = "─", width: int = 72, color: str = DIM) -> str:
    """Return a horizontal rule string."""
    return f"{color}{char * width}{NC}"


# ─── ASCII banner ───────────────────────────────────────────────────────────

TEMS_LOGO_LINES = [
    f"{ORANGE}  ████████╗ ███████╗ ███╗   ███╗ ███████╗{NC}",
    f"{ORANGE}  ╚══██╔══╝ ██╔════╝ ████╗ ████║ ██╔════╝{NC}",
    f"{ORANGE}     ██║    █████╗   ██╔████╔██║ ███████╗{NC}",
    f"{ORANGE}     ██║    ██╔══╝   ██║╚██╔╝██║ ╚════██║{NC}",
    f"{ORANGE}     ██║    ███████╗ ██║ ╚═╝ ██║ ███████║{NC}",
    f"{ORANGE}     ╚═╝    ╚══════╝ ╚═╝     ╚═╝ ╚══════╝{NC}",
]


def print_header(animate: bool = True):
    """Print the TEMS header with logo."""
    _real_print()
    if animate:
        for line in TEMS_LOGO_LINES:
            typewrite(line, speed=0.001)
            time.sleep(0.03)
        typewrite(f"  {dim(f'Tsana Extended Management System v{TEMS_VERSION}')}", speed=SPEED_FAST)
    else:
        for line in TEMS_LOGO_LINES:
            _real_print(line)
        _real_print(f"  {dim(f'Tsana Extended Management System v{TEMS_VERSION}')}")
    _real_print()


# ─── Status panel ───────────────────────────────────────────────────────────

def gather_status(config: Config) -> dict[str, str]:
    """Gather server status info for the dashboard. Non-fatal on errors."""
    status: dict[str, str] = {
        "mods":    "—",
        "size":    "—",
        "mission": "—",
        "steam":   "—",
        "mods_list_count": "—",
    }

    try:
        mapping = read_mod_mapping(Path(config.mod_mapping_file))
        status["mods"] = str(len(mapping))
    except Exception:
        pass

    try:
        lgsm_mods = read_lgsm_mods(Path(config.lgsm_config))
        status["mods_list_count"] = str(len(lgsm_mods))
    except Exception:
        pass

    try:
        mods_path = Path(config.server_mods_dir)
        if mods_path.exists():
            total = sum(f.stat().st_size for f in mods_path.rglob("*") if f.is_file())
            gb = total / (1024 ** 3)
            status["size"] = f"{gb:.1f} GB" if gb >= 1 else f"{total / (1024**2):.0f} MB"
    except Exception:
        pass

    try:
        status["mission"] = Path(config.mission_dir).name
    except Exception:
        pass

    status["steam"] = config.steam_user or "not set"
    return status


def print_status_block(status: dict[str, str]):
    """Print the server status summary as a compact block."""
    typewrite(rule(), speed=0.001)
    typewrite(f"  {orange('◈')} {bold('SERVER STATUS')}", speed=SPEED_FAST)
    typewrite(rule(), speed=0.001)
    typewrite(
        f"  Mods Installed: {Colors.yellow(status['mods']):<10}"
        f"  Load Order: {Colors.yellow(status['mods_list_count']):<10}"
        f"  Mods Dir: {Colors.yellow(status['size'])}",
        speed=SPEED_FAST,
    )
    typewrite(
        f"  Active Mission: {Colors.yellow(status['mission']):<22}"
        f"  Steam User: {Colors.yellow(status['steam'])}",
        speed=SPEED_FAST,
    )
    typewrite(rule(), speed=0.001)


# ─── Menu ───────────────────────────────────────────────────────────────────

MENU = [
    ("1",  "Install",          "Download & install a single mod"),
    ("2",  "Batch Install",    "Install multiple mods from a list file"),
    ("3",  "Update",           "Update all installed mods"),
    ("4",  "Reorder",          "Change mod load order"),
    ("5",  "Export",           "Export mod list to file"),
    ("6",  "Cleanup",          "Remove mods from config"),
    ("7",  "Backup",           "Back up server data"),
    ("8",  "Restore",          "Restore from a backup archive"),
    ("9",  "XML Merge",        "Merge mod XMLs into mission files"),
    ("10", "Conflicts",        "Detect conflicting mod files"),
    ("11", "Dependencies",     "Check mod dependencies"),
    ("12", "Monitor",          "View server performance stats"),
    ("13", "Settings",         "View current TEMS configuration"),
    ("0",  "Exit",             "Quit TEMS"),
]


def print_menu():
    """Print the main menu options with typewriter effect."""
    _real_print()
    typewrite(f"  {orange('◈')} {bold('MAIN MENU')}", speed=SPEED_FAST)
    _real_print()
    for key, name, desc in MENU:
        key_display = f"[{key}]"
        typewrite(
            f"   {Colors.yellow(key_display):>14}  {name:<18} {dim(desc)}",
            speed=SPEED_FAST,
        )
    _real_print()


# ─── Settings view ──────────────────────────────────────────────────────────

def show_settings(config: Config):
    """Display the current TEMS configuration."""
    clear()
    print_header(animate=False)
    run_with_typewriter(banner, f"TEMS Settings v{TEMS_VERSION}")

    fields = [
        ("Steam User",       config.steam_user or "(not set)"),
        ("Steam Pass",       "****" if config.steam_pass else "(not set)"),
        ("",                 ""),
        ("Server Base Dir",  config.server_base_dir),
        ("Server Files Dir", config.server_files_dir),
        ("Server Mods Dir",  config.server_mods_dir),
        ("Keys Dir",         config.keys_dir),
        ("LGSM Config",      config.lgsm_config),
        ("",                 ""),
        ("SteamCMD Path",    config.steamcmd_path),
        ("Workshop Dir",     config.workshop_dir),
        ("Mod Mapping File", config.mod_mapping_file),
        ("DayZ App ID",      config.dayz_app_id),
        ("",                 ""),
        ("Backup Dir",       config.backup_dir),
        ("Backup Keep",      config.backup_keep),
        ("Rclone Remote",    config.backup_rclone_remote or "(not set)"),
        ("",                 ""),
        ("Mission Dir",      config.mission_dir),
        ("LGSM Script",      config.lgsm_script),
    ]

    for label, value in fields:
        if not label:
            _real_print()
            continue
        exists_marker = ""
        if value and value not in ("(not set)", "****") and "/" in value:
            p = Path(value)
            if p.exists():
                exists_marker = f"  {Colors.green('✓')}"
            else:
                exists_marker = f"  {Colors.red('✗ not found')}"
        typewrite(
            f"  {Colors.cyan(label + ':'):<30} {Colors.yellow(value)}{exists_marker}",
            speed=SPEED_NORMAL,
        )

    _real_print()
    typewrite(dim("  Edit tems.yaml to change these settings."), speed=SPEED_FAST)
    pause_before_menu()


# ─── Mod overview ───────────────────────────────────────────────────────────

def show_mod_overview(config: Config):
    """Display a table of all installed mods with versions and dates."""
    mapping = read_mod_mapping(Path(config.mod_mapping_file))
    mods_dir = Path(config.server_mods_dir)
    lgsm_mods = read_lgsm_mods(Path(config.lgsm_config))

    if not mapping:
        typewrite(Colors.yellow("  No mod mapping found. Install mods first."), speed=SPEED_NORMAL)
        return

    header = f"  {'#':<4} {'Mod Name':<30} {'Workshop ID':<14} {'Version':<12} {'Updated':<12} {'Config'}"
    typewrite(header, speed=SPEED_FAST)
    typewrite(f"  {'─'*4} {'─'*30} {'─'*14} {'─'*12} {'─'*12} {'─'*8}", speed=0.001)

    for i, (wid, name) in enumerate(mapping.items(), 1):
        mod_path = mods_dir / name
        version = get_mod_version(mod_path)
        updated = get_mod_last_updated(mod_path)
        in_config = Colors.green("✓") if name in lgsm_mods else Colors.red("✗")
        typewrite(
            f"  {i:<4} {Colors.yellow(name):<30} {wid:<14} {version:<12} {updated:<12} {in_config}",
            speed=SPEED_FAST,
        )

    _real_print()
    typewrite(dim(f"  {len(mapping)} mod(s) in mapping, {len(lgsm_mods)} in load order"), speed=SPEED_FAST)


# ─── Main loop ──────────────────────────────────────────────────────────────

def main_menu(config: Config):
    """Main menu loop — the heart of the TUI."""

    first_run = True

    while True:
        clear()
        print_header(animate=first_run)
        first_run = False

        status = gather_status(config)
        print_status_block(status)
        print_menu()

        ts = datetime.now().strftime("%H:%M:%S")
        choice = input(f"  {dim(ts)}  {orange('▸')} Choose option: ").strip()

        ns = argparse.Namespace(yes=False)

        if choice == "1":
            clear()
            print_header(animate=False)
            ns.workshop_id = None
            ns.name = None
            ns.manual = False
            run_with_typewriter(cmd_install, ns, config)
            pause_before_menu()

        elif choice == "2":
            clear()
            print_header(animate=False)
            file_path = prompt_input("Enter path to mod list file:")
            if file_path:
                ns.file = file_path
                run_with_typewriter(cmd_batch_install, ns, config)
            else:
                typewrite(Colors.red("  No file specified"), speed=SPEED_NORMAL)
            pause_before_menu()

        elif choice == "3":
            clear()
            print_header(animate=False)
            run_with_typewriter(cmd_update, ns, config)
            pause_before_menu()

        elif choice == "4":
            clear()
            print_header(animate=False)
            run_with_typewriter(cmd_reorder, ns, config)
            pause_before_menu()

        elif choice == "5":
            clear()
            print_header(animate=False)
            ns.output = None
            run_with_typewriter(cmd_export, ns, config)
            pause_before_menu()

        elif choice == "6":
            clear()
            print_header(animate=False)
            run_with_typewriter(cmd_cleanup, ns, config)
            pause_before_menu()

        elif choice == "7":
            clear()
            print_header(animate=False)
            ns.scope = None
            ns.dest = None
            run_with_typewriter(cmd_backup, ns, config)
            pause_before_menu()

        elif choice == "8":
            clear()
            print_header(animate=False)
            ns.backup = None
            run_with_typewriter(cmd_restore, ns, config)
            pause_before_menu()

        elif choice == "9":
            clear()
            print_header(animate=False)
            run_with_typewriter(cmd_xml_merge, ns, config)

        elif choice == "10":
            clear()
            print_header(animate=False)
            run_with_typewriter(cmd_conflicts, ns, config)
            pause_before_menu()

        elif choice == "11":
            clear()
            print_header(animate=False)
            run_with_typewriter(cmd_deps, ns, config)
            pause_before_menu()

        elif choice == "12":
            clear()
            print_header(animate=False)
            run_with_typewriter(cmd_monitor, ns, config)
            pause_before_menu()

        elif choice == "13":
            show_settings(config)

        elif choice in ("0", "q", "Q"):
            clear()
            print_header(animate=False)
            typewrite(Colors.green("  Goodbye!"), speed=SPEED_SLOW)
            _real_print()
            return

        elif choice in ("m", "mods"):
            clear()
            print_header(animate=False)
            run_with_typewriter(banner, "Installed Mods Overview")
            show_mod_overview(config)
            pause_before_menu()

        else:
            pass


# ─── Entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="tems_tui.py",
        description="TEMS Enhanced Terminal Interface",
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to tems.yaml config file",
        default=None,
    )
    args = parser.parse_args()

    config_path = Path(args.config) if args.config else None
    config = Config(config_path)

    try:
        main_menu(config)
    except KeyboardInterrupt:
        _real_print()
        typewrite(Colors.green("\n  Interrupted. Goodbye!"), speed=SPEED_SLOW)
        _real_print()


if __name__ == "__main__":
    main()
