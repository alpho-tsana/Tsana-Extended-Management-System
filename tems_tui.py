#!/usr/bin/env python3
# =============================================================================
# TEMS TUI - Textual Terminal UI for TEMS
# Requires: pip install textual
# =============================================================================

from __future__ import annotations

import io
import os
import re
import shutil
import sys
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    DataTable,
    Footer,
    Input,
    Label,
    ProgressBar,
    RadioButton,
    RadioSet,
    RichLog,
    Static,
)

# Import TEMS internals
from tems import (
    BACKUP_SCOPES,
    Config,
    TEMS_VERSION,
    XMLMerger,
    add_mod_to_config,
    check_steam_credentials,
    cmd_conflicts,
    cmd_deps,
    cmd_monitor,
    copy_keys,
    create_backup_archive,
    ensure_at_prefix,
    gather_backup_paths,
    install_single_mod,
    list_backup_archives,
    lowercase_contents,
    read_lgsm_mods,
    read_mod_mapping,
    restore_backup_archive,
    rotate_backups,
    run_steamcmd_script,
    upload_rclone,
    validate_workshop_id,
    get_mod_last_updated,
    get_mod_version,
    write_lgsm_mods,
    write_mod_mapping,
)

TEMS_ASCII = r"""  ████████╗ ███████╗ ███╗   ███╗ ███████╗
  ╚══██╔══╝ ██╔════╝ ████╗ ████║ ██╔════╝
     ██║    █████╗   ██╔████╔██║ ███████╗
     ██║    ██╔══╝   ██║╚██╔╝██║ ╚════██║
     ██║    ███████╗ ██║ ╚═╝ ██║ ███████║
     ╚═╝    ╚══════╝ ╚═╝     ╚═╝ ╚══════╝
  Tsana Extended Management System v""" + TEMS_VERSION

MENU_ITEMS = [
    ("1", "Install",          "Download & install a single mod"),
    ("2", "Batch Install",    "Install multiple mods from a list file"),
    ("3", "Update",           "Update all installed mods"),
    ("4", "Reorder",          "Change mod load order"),
    ("5", "Export",           "Export mod list to file"),
    ("6", "Cleanup",          "Remove mods from config"),
    ("7", "Backup",           "Back up server data"),
    ("8", "XML Merge",        "Merge mod XMLs into mission files"),
    ("r", "Restore",          "Restore from a backup archive"),
    ("c", "Conflicts",        "Detect conflicting mod files"),
    ("d", "Deps",             "Check mod dependencies"),
    ("m", "Monitor",          "View server performance stats"),
    ("q", "Exit",             "Quit TEMS"),
]


TIPH_ASCII = (
    "  ████████╗ ██╗ ██████╗ ██╗  ██╗\n"
    "     ██╔══╝ ██║ ██╔══██╗ ██║  ██║\n"
    "     ██║    ██║ ██████╔╝ ███████║\n"
    "     ██║    ██║ ██╔═══╝  ██╔══██║\n"
    "     ██║    ██║ ██║      ██║  ██║\n"
    "     ╚═╝    ╚═╝ ╚═╝      ╚═╝  ╚═╝"
)


# ─── Shared components ──────────────────────────────────────────────────────

class TEMSHeader(Static):
    """Persistent ASCII art banner."""

    def __init__(self) -> None:
        super().__init__(TEMS_ASCII, id="tems-header")


class LogWriter:
    """Redirect print() output to a RichLog widget from a worker thread."""

    def __init__(self, log_widget: RichLog, app: App) -> None:
        self._log = log_widget
        self._app = app

    def write(self, text: str) -> int:
        # Strip ANSI escape codes for clean display
        clean = re.sub(r'\033\[[0-9;]*m', '', text)
        if clean.strip():
            self._app.call_from_thread(self._log.write, clean.rstrip('\n'))
        return len(text)

    def flush(self) -> None:
        pass


# ─── Confirm Modal ──────────────────────────────────────────────────────────

class ConfirmModal(ModalScreen[bool]):
    """Yes/No confirmation dialog."""

    BINDINGS = [
        Binding("y", "confirm_yes", "Yes", show=True),
        Binding("n", "confirm_no", "No", show=True),
        Binding("escape", "confirm_no", "Cancel", show=True),
    ]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-dialog"):
            yield Static(self.message)
            yield Static("  [y] Yes   [n] No   [Esc] Cancel", classes="key-hint")

    def action_confirm_yes(self) -> None:
        self.dismiss(True)

    def action_confirm_no(self) -> None:
        self.dismiss(False)


# ─── Base screen with header ────────────────────────────────────────────────

class TEMSScreen(Screen):
    """Base screen that includes the header and a back binding."""

    BINDINGS = [
        Binding("escape", "go_back", "Back"),
    ]

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ─── Main Menu Screen ──────────────────────────────────────────────────────

class MainMenuScreen(Screen):
    """
    Main dashboard: status panel left, menu right, event log bottom.
    Matches TIPH layout style.
    """

    BINDINGS = [
        Binding("1", "menu_1", "Install",       show=True),
        Binding("2", "menu_2", "Batch Install",  show=True),
        Binding("3", "menu_3", "Update",         show=True),
        Binding("4", "menu_4", "Reorder",        show=True),
        Binding("5", "menu_5", "Export",         show=True),
        Binding("6", "menu_6", "Cleanup",        show=True),
        Binding("7", "menu_7", "Backup",         show=True),
        Binding("8", "menu_8", "XML Merge",      show=True),
        Binding("r", "menu_r", "Restore",        show=False),
        Binding("c", "menu_c", "Conflicts",      show=False),
        Binding("d", "menu_d", "Deps",           show=False),
        Binding("m", "menu_m", "Monitor",        show=False),
        Binding("q", "menu_q", "Exit",           show=True),
        Binding("9", "menu_q", "Exit",           show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="main-layout"):
            with Horizontal(id="main-top"):

                # Left: status panel
                with Vertical(id="status-panel", classes="panel-orange"):
                    yield Label("◈ SERVER STATUS", classes="panel-title")
                    yield Label(TIPH_ASCII, id="tems-ascii")
                    yield Label(f"v{TEMS_VERSION}", classes="field-value-orange")
                    yield Label("─" * 24, classes="divider")
                    yield Label("Mods Installed",  classes="field-label")
                    yield Label("—", id="lbl-mods",    classes="field-value-orange")
                    yield Label("Mods Dir Size",   classes="field-label")
                    yield Label("—", id="lbl-size",    classes="field-value")
                    yield Label("Active Mission",  classes="field-label")
                    yield Label("—", id="lbl-mission", classes="field-value")
                    yield Label("─" * 24, classes="divider")
                    yield Label("Steam User",      classes="field-label")
                    yield Label("—", id="lbl-steam",   classes="field-value")

                # Right: menu
                with Vertical(id="menu-panel", classes="panel"):
                    yield Label("◈ MAIN MENU", classes="panel-title")
                    for key, name, desc in MENU_ITEMS:
                        yield Static(
                            f"  [{key}]  {name}  —  {desc}",
                            classes="menu-label",
                        )

            # Bottom: event log
            with Vertical(id="log-panel", classes="panel"):
                yield Label("◈ EVENT LOG", classes="panel-title")
                yield RichLog(id="event-log", markup=True, highlight=False, wrap=False)

        yield Footer()

    def on_mount(self) -> None:
        self._refresh_status()
        self._log(f"[orange1]TEMS v{TEMS_VERSION} started.[/] Ready.")

    def _refresh_status(self) -> None:
        cfg = self.app.config
        try:
            mapping = read_mod_mapping(Path(cfg.mod_mapping_file))
            mod_count = str(len(mapping))
        except Exception:
            mod_count = "—"
        try:
            mods_path = Path(cfg.server_mods_dir)
            if mods_path.exists():
                total = sum(f.stat().st_size for f in mods_path.rglob("*") if f.is_file())
                gb = total / (1024 ** 3)
                size_str = f"{gb:.2f} GB" if gb >= 1 else f"{total / (1024**2):.0f} MB"
            else:
                size_str = "dir not found"
        except Exception:
            size_str = "—"
        try:
            mission = Path(cfg.mission_dir).name
        except Exception:
            mission = "—"
        steam = cfg.steam_user or "not set"
        self.query_one("#lbl-mods",    Label).update(mod_count)
        self.query_one("#lbl-size",    Label).update(size_str)
        self.query_one("#lbl-mission", Label).update(mission)
        self.query_one("#lbl-steam",   Label).update(steam)

    def _log(self, message: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.query_one("#event-log", RichLog).write(f"[dim]{ts}[/]  {message}")

    def _handle_choice(self, choice: str) -> None:
        config = self.app.config
        labels = {
            "1": "Install",   "2": "Batch Install", "3": "Update",    "4": "Reorder",
            "5": "Export",    "6": "Cleanup",        "7": "Backup",    "8": "XML Merge",
            "r": "Restore",   "c": "Conflicts",      "d": "Deps",      "m": "Monitor",
        }
        screen_factories = {
            "1": lambda: InstallScreen(config),
            "2": lambda: BatchInstallScreen(config),
            "3": lambda: UpdateScreen(config),
            "4": lambda: ReorderScreen(config),
            "5": lambda: ExportScreen(config),
            "6": lambda: CleanupScreen(config),
            "7": lambda: BackupScreen(config),
            "8": lambda: XMLMergeScreen(config),
            "r": lambda: RestoreScreen(config),
            "c": lambda: ConflictsScreen(config),
            "d": lambda: DepsScreen(config),
            "m": lambda: MonitorScreen(config),
        }
        if choice in ("q", "9"):
            self.app.exit()
            return
        factory = screen_factories.get(choice)
        if factory:
            self._log(f"[orange1]→[/] Opening [bold]{labels.get(choice, choice)}[/]...")
            def _on_return(_, c=choice):
                self._refresh_status()
                self._log(f"[dim]← Returned from {labels.get(c, c)}.[/]")
            self.app.push_screen(factory(), _on_return)

    def action_menu_1(self) -> None: self._handle_choice("1")
    def action_menu_2(self) -> None: self._handle_choice("2")
    def action_menu_3(self) -> None: self._handle_choice("3")
    def action_menu_4(self) -> None: self._handle_choice("4")
    def action_menu_5(self) -> None: self._handle_choice("5")
    def action_menu_6(self) -> None: self._handle_choice("6")
    def action_menu_7(self) -> None: self._handle_choice("7")
    def action_menu_8(self) -> None: self._handle_choice("8")
    def action_menu_r(self) -> None: self._handle_choice("r")
    def action_menu_c(self) -> None: self._handle_choice("c")
    def action_menu_d(self) -> None: self._handle_choice("d")
    def action_menu_m(self) -> None: self._handle_choice("m")
    def action_menu_q(self) -> None: self._handle_choice("q")
    def action_menu_9(self) -> None: self._handle_choice("q")


# ─── Install Screen ────────────────────────────────────────────────────────

class InstallScreen(TEMSScreen):
    """Install a single mod (Workshop or Manual)."""

    BINDINGS = [
        Binding("enter", "do_install", "Install", show=True),
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self._running = False

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Install a Mod", classes="section-title")
            yield Static("Choose installation method:", classes="info-text")
            yield RadioSet(
                RadioButton("Steam Workshop Download", value=True, id="radio-workshop"),
                RadioButton("Manual Install (mod already uploaded)", id="radio-manual"),
                id="install-method",
            )
            yield Static("Workshop Details", classes="section-title")
            yield Label("Workshop ID:")
            yield Input(placeholder="e.g. 2545327648", id="workshop-id")
            yield Label("Mod Name:")
            yield Input(placeholder="e.g. @Banov", id="mod-name")
            yield Static("  [Enter] Install   [Esc] Back", classes="key-hint")
            yield RichLog(id="install-log", wrap=True)
        yield Footer()

    def action_do_install(self) -> None:
        self._start_install()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._start_install()

    def _start_install(self) -> None:
        if self._running:
            return
        method_set = self.query_one("#install-method", RadioSet)
        is_workshop = method_set.pressed_index == 0

        if is_workshop:
            wid = self.query_one("#workshop-id", Input).value.strip()
            name = self.query_one("#mod-name", Input).value.strip()
            if not wid or not validate_workshop_id(wid):
                self.notify("Invalid Workshop ID (must be numeric)", severity="error")
                return
            if not name:
                self.notify("Mod name is required", severity="error")
                return
            self._running = True
            self._do_workshop_install(wid, name)
        else:
            self._do_manual_install()

    @work(thread=True)
    def _do_workshop_install(self, workshop_id: str, mod_name: str) -> None:
        log = self.query_one("#install-log", RichLog)
        writer = LogWriter(log, self.app)
        with redirect_stdout(writer), redirect_stderr(writer):
            try:
                install_single_mod(workshop_id, mod_name, self.config, auto_yes=True)
            except Exception as e:
                self.app.call_from_thread(log.write, f"Error: {e}")
        self.app.call_from_thread(self._finish_install)

    def _do_manual_install(self) -> None:
        log = self.query_one("#install-log", RichLog)
        mods_dir = Path(self.config.server_mods_dir)
        if not mods_dir.is_dir():
            self.notify(f"Mods directory not found: {mods_dir}", severity="error")
            return
        available = sorted(
            [d for d in mods_dir.iterdir() if d.is_dir() and d.name.startswith("@")]
        )
        if not available:
            self.notify("No mods with @ prefix found in mods directory", severity="warning")
            return
        log.write("[bold]Available mods for manual install:[/bold]")
        for i, mod in enumerate(available, 1):
            log.write(f"  {i}. {mod.name}")
        log.write("\nEnter the mod number in the Workshop ID field and press Enter again.")
        log.write("(Manual install will process the mod at that index)")

    def _finish_install(self) -> None:
        self._running = False
        self.notify("Installation complete!", severity="information")


# ─── Batch Install Screen ──────────────────────────────────────────────────

class BatchInstallScreen(TEMSScreen):
    """Batch install mods from a list file."""

    BINDINGS = [
        Binding("p", "do_preview", "Preview", show=True),
        Binding("enter", "do_batch_install", "Install All", show=True),
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self._running = False

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Batch Install Mods", classes="section-title")
            yield Static(
                "Provide a mod list file with format: ModName - https://steamcommunity.com/sharedfiles/filedetails/?id=XXXXX",
                classes="info-text",
            )
            yield Label("Mod list file path:")
            yield Input(placeholder="e.g. my_mod_list.txt", id="batch-file")
            yield Static("  [p] Preview   [Enter] Install All   [Esc] Back", classes="key-hint")
            yield DataTable(id="batch-table")
            yield RichLog(id="batch-log", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#batch-table", DataTable)
        table.add_columns("#", "Mod Name", "Workshop ID")

    def action_do_preview(self) -> None:
        self._preview_file()

    def action_do_batch_install(self) -> None:
        self._start_batch()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._start_batch()

    def _parse_mod_file(self, filepath: str) -> list[tuple[str, str]]:
        pattern = re.compile(
            r'^(.+?)\s*-\s*https://steamcommunity\.com/sharedfiles/filedetails/\?id=(\d+)'
        )
        mods = []
        for line in Path(filepath).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = pattern.match(line)
            if m:
                name = ensure_at_prefix(m.group(1).strip().replace(" ", ""))
                mods.append((name, m.group(2)))
        return mods

    def _preview_file(self) -> None:
        filepath = self.query_one("#batch-file", Input).value.strip()
        if not filepath or not Path(filepath).exists():
            self.notify("File not found", severity="error")
            return
        mods = self._parse_mod_file(filepath)
        table = self.query_one("#batch-table", DataTable)
        table.clear()
        for i, (name, wid) in enumerate(mods, 1):
            table.add_row(str(i), name, wid)
        self.notify(f"Found {len(mods)} mod(s)")

    def _start_batch(self) -> None:
        if self._running:
            return
        filepath = self.query_one("#batch-file", Input).value.strip()
        if not filepath or not Path(filepath).exists():
            self.notify("File not found", severity="error")
            return
        self._running = True
        self._do_batch_install(filepath)

    @work(thread=True)
    def _do_batch_install(self, filepath: str) -> None:
        log = self.query_one("#batch-log", RichLog)
        writer = LogWriter(log, self.app)
        mods = self._parse_mod_file(filepath)
        total = len(mods)

        if not self.config.steam_user or not self.config.steam_pass:
            self.app.call_from_thread(
                log.write, "Error: Steam credentials not configured in tems.yaml"
            )
            self.app.call_from_thread(self._finish_batch)
            return

        with redirect_stdout(writer), redirect_stderr(writer):
            # Build SteamCMD script
            script_lines = [f"login {self.config.steam_user} {self.config.steam_pass}"]
            for _name, wid in mods:
                script_lines.append(f"workshop_download_item {self.config.dayz_app_id} {wid}")
            script_lines.append("quit")

            self.app.call_from_thread(
                log.write, f"Downloading {total} mod(s) via SteamCMD (as {self.config.steam_user})..."
            )

            def _batch_line(line: str):
                self.app.call_from_thread(log.write, f"[dim]{line}[/]")

            dl_result = run_steamcmd_script(self.config, script_lines, on_line=_batch_line)
            if dl_result != 0:
                self.app.call_from_thread(
                    log.write,
                    f"SteamCMD exited with error code {dl_result}. "
                    "Check credentials in tems.yaml or run SteamCMD manually to complete Steam Guard.",
                )

            # Process each mod
            keys_dir = Path(self.config.keys_dir)
            keys_dir.mkdir(parents=True, exist_ok=True)
            mods_dir = Path(self.config.server_mods_dir)
            lgsm_path = Path(self.config.lgsm_config)

            for idx, (mod_name, wid) in enumerate(mods, 1):
                self.app.call_from_thread(
                    log.write, f"\n[{idx}/{total}] Processing: {mod_name} (ID: {wid})"
                )
                workshop_path = Path(self.config.workshop_dir) / wid
                dest_path = mods_dir / mod_name

                if not workshop_path.is_dir():
                    self.app.call_from_thread(
                        log.write, f"  FAILED: Workshop files not found for {mod_name}"
                    )
                    continue

                if dest_path.exists():
                    shutil.rmtree(dest_path)
                try:
                    shutil.copytree(str(workshop_path), str(dest_path))
                except OSError:
                    self.app.call_from_thread(
                        log.write, f"  FAILED: Could not copy files for {mod_name}"
                    )
                    continue

                copy_keys(dest_path, keys_dir)
                lowercase_contents(dest_path)

                try:
                    shutil.rmtree(workshop_path)
                except OSError:
                    pass

                write_mod_mapping(Path(self.config.mod_mapping_file), wid, mod_name)
                if lgsm_path.exists():
                    add_mod_to_config(lgsm_path, mod_name)

                self.app.call_from_thread(log.write, f"  OK: {mod_name} installed")

        self.app.call_from_thread(self._finish_batch)

    def _finish_batch(self) -> None:
        self._running = False
        self.notify("Batch installation complete!", severity="information")


# ─── Update Screen ──────────────────────────────────────────────────────────

class UpdateScreen(TEMSScreen):
    """Update all mapped mods."""

    BINDINGS = [
        Binding("enter", "do_update", "Update All", show=True),
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self._running = False

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Update All Mods", classes="section-title")
            yield Static("Mods from your mapping file will be updated via SteamCMD.", classes="info-text")
            yield DataTable(id="update-table")
            yield Static("  [Enter] Update All   [Esc] Back", classes="key-hint")
            yield RichLog(id="update-log", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#update-table", DataTable)
        table.add_columns("#", "Mod Name", "Workshop ID", "Last Updated", "Version")
        mapping = read_mod_mapping(Path(self.config.mod_mapping_file))
        mods_dir = Path(self.config.server_mods_dir)
        for i, (wid, name) in enumerate(mapping.items(), 1):
            mod_path = mods_dir / name
            last_updated = get_mod_last_updated(mod_path)
            version      = get_mod_version(mod_path)
            table.add_row(str(i), name, wid, last_updated, version)
        if not mapping:
            self.query_one("#update-log", RichLog).write(
                "No mod mapping found. Install mods first."
            )

    def action_do_update(self) -> None:
        if self._running:
            return
        self._running = True
        self._do_update()

    @work(thread=True)
    def _do_update(self) -> None:
        log = self.query_one("#update-log", RichLog)
        writer = LogWriter(log, self.app)

        mapping = read_mod_mapping(Path(self.config.mod_mapping_file))
        if not mapping:
            self.app.call_from_thread(log.write, "No mods to update.")
            self.app.call_from_thread(self._finish_update)
            return

        if not self.config.steam_user or not self.config.steam_pass:
            self.app.call_from_thread(
                log.write, "Error: Steam credentials not configured in tems.yaml"
            )
            self.app.call_from_thread(self._finish_update)
            return

        with redirect_stdout(writer), redirect_stderr(writer):
            script_lines = [f"login {self.config.steam_user} {self.config.steam_pass}"]
            for wid in mapping:
                script_lines.append(
                    f"workshop_download_item {self.config.dayz_app_id} {wid} validate"
                )
            script_lines.append("quit")

            self.app.call_from_thread(
                log.write, f"Downloading updates for {len(mapping)} mod(s) (as {self.config.steam_user})..."
            )

            def _update_line(line: str):
                self.app.call_from_thread(log.write, f"[dim]{line}[/]")

            dl_result = run_steamcmd_script(self.config, script_lines, on_line=_update_line)
            if dl_result != 0:
                self.app.call_from_thread(
                    log.write,
                    f"SteamCMD exited with error code {dl_result}. "
                    "Check credentials in tems.yaml or run SteamCMD manually to complete Steam Guard.",
                )

            keys_dir = Path(self.config.keys_dir)
            keys_dir.mkdir(parents=True, exist_ok=True)
            mods_dir = Path(self.config.server_mods_dir)

            for idx, (wid, mod_name) in enumerate(mapping.items(), 1):
                self.app.call_from_thread(
                    log.write,
                    f"\n[{idx}/{len(mapping)}] Processing: {mod_name} (ID: {wid})",
                )
                workshop_path = Path(self.config.workshop_dir) / wid
                dest_path = mods_dir / mod_name

                if not workshop_path.is_dir():
                    self.app.call_from_thread(
                        log.write, f"  SKIPPED: Workshop files not found for {mod_name}"
                    )
                    continue

                if dest_path.exists():
                    shutil.rmtree(dest_path)

                try:
                    shutil.copytree(str(workshop_path), str(dest_path))
                except OSError:
                    self.app.call_from_thread(
                        log.write, f"  FAILED: Could not copy files for {mod_name}"
                    )
                    continue

                copy_keys(dest_path, keys_dir)
                lowercase_contents(dest_path)

                try:
                    shutil.rmtree(workshop_path)
                except OSError:
                    pass

                self.app.call_from_thread(log.write, f"  OK: {mod_name} updated")

        self.app.call_from_thread(self._finish_update)

    def _finish_update(self) -> None:
        self._running = False
        self.notify("All mods updated!", severity="information")


# ─── Reorder Screen ────────────────────────────────────────────────────────

class ReorderScreen(TEMSScreen):
    """Interactive mod load order manager with DataTable."""

    BINDINGS = [
        Binding("k", "move_up", "Move Up", show=True),
        Binding("j", "move_down", "Move Down", show=True),
        Binding("s", "save_order", "Save", show=True),
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.mods: list[str] = []

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Mod Load Order", classes="section-title")
            yield Static(
                "Select a mod and use j/k keys to reorder. Maps first, frameworks early.",
                classes="info-text",
            )
            yield DataTable(id="reorder-table")
            yield Static("  [k] Move Up   [j] Move Down   [s] Save   [Esc] Back", classes="key-hint")
        yield Footer()

    def on_mount(self) -> None:
        self.mods = read_lgsm_mods(Path(self.config.lgsm_config))
        self._refresh_table()

    def _refresh_table(self) -> None:
        table = self.query_one("#reorder-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Position", "Mod Name")
        for i, mod in enumerate(self.mods, 1):
            table.add_row(str(i), mod, key=str(i))
        if self.mods:
            table.move_cursor(row=0)

    def _get_cursor_row(self) -> int | None:
        table = self.query_one("#reorder-table", DataTable)
        if not self.mods:
            return None
        return table.cursor_row

    def _swap(self, idx: int, direction: int) -> None:
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.mods):
            return
        self.mods[idx], self.mods[new_idx] = self.mods[new_idx], self.mods[idx]
        self._refresh_table()
        table = self.query_one("#reorder-table", DataTable)
        table.move_cursor(row=new_idx)

    def action_move_up(self) -> None:
        row = self._get_cursor_row()
        if row is not None:
            self._swap(row, -1)

    def action_move_down(self) -> None:
        row = self._get_cursor_row()
        if row is not None:
            self._swap(row, 1)

    def action_save_order(self) -> None:
        write_lgsm_mods(Path(self.config.lgsm_config), self.mods)
        self.notify("Load order saved!", severity="information")
        self.app.pop_screen()


# ─── Export Screen ──────────────────────────────────────────────────────────

class ExportScreen(TEMSScreen):
    """Export mod list to a file."""

    BINDINGS = [
        Binding("enter", "do_export", "Export", show=True),
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Export Mod List", classes="section-title")
            yield Static(
                "Export your mod mapping to a file compatible with batch-install.",
                classes="info-text",
            )
            yield Label("Output filename:")
            yield Input(
                placeholder="my_mod_list.txt", value="my_mod_list.txt", id="export-filename"
            )
            yield Static("  [Enter] Export   [Esc] Back", classes="key-hint")
            yield RichLog(id="export-log", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#export-log", RichLog)
        mapping = read_mod_mapping(Path(self.config.mod_mapping_file))
        if mapping:
            log.write(f"Found {len(mapping)} mod(s) in mapping file:")
            for wid, name in mapping.items():
                log.write(f"  {name} (ID: {wid})")
        else:
            log.write("No mod mapping found. Install mods first.")

    def action_do_export(self) -> None:
        self._do_export()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_export()

    def _do_export(self) -> None:
        output = self.query_one("#export-filename", Input).value.strip()
        if not output:
            output = "my_mod_list.txt"
        if not output.endswith(".txt"):
            output += ".txt"

        mapping = read_mod_mapping(Path(self.config.mod_mapping_file))
        if not mapping:
            self.notify("No mod mapping to export", severity="error")
            return

        with open(output, "w") as f:
            f.write("# DayZ Server Mod List\n")
            f.write("# Format: ModName - https://steamcommunity.com/sharedfiles/filedetails/?id=WORKSHOP_ID\n")
            f.write("# Generated by TEMS TUI\n\n")
            for wid, mod_name in mapping.items():
                display_name = mod_name.lstrip("@")
                f.write(
                    f"{display_name} - https://steamcommunity.com/sharedfiles/filedetails/?id={wid}\n"
                )

        log = self.query_one("#export-log", RichLog)
        log.write(f"\nExported {len(mapping)} mod(s) to {output}")
        self.notify(f"Exported to {output}", severity="information")


# ─── Cleanup Screen ────────────────────────────────────────────────────────

class CleanupScreen(TEMSScreen):
    """Remove mods from LGSM config."""

    BINDINGS = [
        Binding("d", "remove_selected", "Remove Selected", show=True),
        Binding("x", "clear_all", "Clear All", show=True),
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.mods: list[str] = []

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Cleanup Mods Config", classes="section-title")
            yield Static(
                "Select a mod from the table, then remove it or clear all.",
                classes="info-text",
            )
            yield DataTable(id="cleanup-table")
            yield Static("  [d] Remove Selected   [x] Clear All   [Esc] Back", classes="key-hint")
        yield Footer()

    def on_mount(self) -> None:
        self._load_mods()

    def _load_mods(self) -> None:
        self.mods = read_lgsm_mods(Path(self.config.lgsm_config))
        table = self.query_one("#cleanup-table", DataTable)
        table.clear(columns=True)
        table.add_columns("#", "Mod Name")
        for i, mod in enumerate(self.mods, 1):
            table.add_row(str(i), mod, key=str(i))

    def action_remove_selected(self) -> None:
        self._remove_selected()

    def action_clear_all(self) -> None:
        self.app.push_screen(
            ConfirmModal("Remove ALL mods from config?"),
            callback=self._on_clear_confirm,
        )

    def _remove_selected(self) -> None:
        table = self.query_one("#cleanup-table", DataTable)
        if not self.mods:
            self.notify("No mods to remove", severity="warning")
            return
        row = table.cursor_row
        if row is not None and 0 <= row < len(self.mods):
            removed = self.mods.pop(row)
            write_lgsm_mods(Path(self.config.lgsm_config), self.mods)
            self._load_mods()
            self.notify(f"Removed {removed}", severity="information")

    def _on_clear_confirm(self, confirmed: bool) -> None:
        if confirmed:
            self.mods = []
            write_lgsm_mods(Path(self.config.lgsm_config), [])
            self._load_mods()
            self.notify("All mods cleared from config", severity="information")


# ─── Backup Screen ──────────────────────────────────────────────────────────

class BackupScreen(TEMSScreen):
    """Multi-step backup wizard."""

    BINDINGS = [
        Binding("enter", "start_backup", "Start Backup", show=True),
        Binding("escape", "go_back", "Back", show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self._running = False

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Backup Server Data", classes="section-title")

            yield Static("Step 1: What to back up", classes="section-title")
            yield RadioSet(
                RadioButton("World data (mpmissions/persistence)", value=True, id="scope-world"),
                RadioButton("Mods (serverfiles/mods)", id="scope-mods"),
                RadioButton("Configs (tems.yaml, LGSM, keys)", id="scope-configs"),
                RadioButton("World + Configs (recommended)", id="scope-world-configs"),
                RadioButton("Everything (world + mods + configs)", id="scope-everything"),
                id="scope-set",
            )

            yield Static("Step 2: Destination", classes="section-title")
            yield RadioSet(
                RadioButton("Local disk", value=True, id="dest-local"),
                RadioButton("rclone remote", id="dest-rclone"),
                RadioButton("Both", id="dest-both"),
                id="dest-set",
            )

            yield Static("  [Enter] Start Backup   [Esc] Back", classes="key-hint")
            yield ProgressBar(id="backup-progress", total=100, show_eta=False)
            yield RichLog(id="backup-log", wrap=True)
        yield Footer()

    def action_start_backup(self) -> None:
        if self._running:
            return
        self._running = True
        self._do_backup()

    @work(thread=True)
    def _do_backup(self) -> None:
        log = self.query_one("#backup-log", RichLog)
        writer = LogWriter(log, self.app)

        scope_set = self.query_one("#scope-set", RadioSet)
        scope_idx = scope_set.pressed_index
        scope_map = {
            0: (["world"], "world"),
            1: (["mods"], "mods"),
            2: (["configs"], "configs"),
            3: (["world", "configs"], "world-configs"),
            4: (["world", "mods", "configs"], "everything"),
        }
        scopes, label = scope_map.get(scope_idx, (["world", "configs"], "world-configs"))

        dest_set = self.query_one("#dest-set", RadioSet)
        dest_idx = dest_set.pressed_index
        dest_map = {0: ["local"], 1: ["rclone"], 2: ["local", "rclone"]}
        dests = dest_map.get(dest_idx, ["local"])

        with redirect_stdout(writer), redirect_stderr(writer):
            source_paths = gather_backup_paths(self.config, scopes)
            if not source_paths:
                self.app.call_from_thread(log.write, "No files found for selected scope.")
                self.app.call_from_thread(self._finish_backup)
                return

            self.app.call_from_thread(
                log.write, f"Backing up: {', '.join(scopes)} -> {', '.join(dests)}"
            )

            backup_dir = Path(self.config.backup_dir)
            archive = create_backup_archive(source_paths, backup_dir, label)

            if "rclone" in dests:
                remote = self.config.backup_rclone_remote
                if remote:
                    upload_rclone(archive, remote)
                else:
                    self.app.call_from_thread(
                        log.write, "Warning: No rclone remote configured in tems.yaml"
                    )

            keep = int(self.config.backup_keep)
            if "local" in dests and keep > 0:
                rotate_backups(backup_dir, keep)

            if "rclone" in dests and "local" not in dests:
                archive.unlink(missing_ok=True)
                self.app.call_from_thread(
                    log.write, "Local archive removed (rclone-only mode)"
                )

        self.app.call_from_thread(self._finish_backup)

    def _finish_backup(self) -> None:
        self._running = False
        pb = self.query_one("#backup-progress", ProgressBar)
        pb.update(progress=100)
        self.notify("Backup complete!", severity="information")


# ─── XML Merge Screen ──────────────────────────────────────────────────────

class XMLMergeScreen(TEMSScreen):
    """XML merger submenu mirroring the CLI xml-merge menu."""

    BINDINGS = [
        Binding("1", "opt_1", "Quick Merge", show=True),
        Binding("2", "opt_2", "Merge Specific", show=True),
        Binding("3", "opt_3", "List Mods", show=True),
        Binding("4", "opt_4", "Switch Mission", show=True),
        Binding("5", "opt_5", "Auto-detect", show=True),
        Binding("6", "opt_6", "Merge Settings", show=True),
        Binding("escape", "go_back", "Back"),
    ]

    XML_MENU = [
        ("1", "Quick Merge", "Auto-scan mods & merge all"),
        ("2", "Merge Specific", "Merge a specific mod folder"),
        ("3", "List Mods", "Show mods and their XML files"),
        ("4", "Switch Mission", "Change active mission"),
        ("5", "Auto-detect", "Scan for new mission folders"),
        ("6", "Merge Settings", "View/change merge rules"),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self.merger = XMLMerger(config)

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("XML Merger", classes="section-title")
            yield Static(
                f"Active mission: {self.merger.config.get('active_mission', 'Not set')}",
                classes="info-text",
                id="active-mission-label",
            )
            for key, name, desc in self.XML_MENU:
                yield Static(
                    f"  [{key}]  {name}  —  {desc}",
                    classes="menu-label",
                )
            yield Label("Mod folder path (for Merge Specific):")
            yield Input(placeholder="e.g. /path/to/@ModName", id="xml-mod-path")
            yield RichLog(id="xml-log", wrap=True)
        yield Footer()

    def _handle_xml_choice(self, choice: int) -> None:
        if choice == 1:
            self._quick_merge()
        elif choice == 2:
            self._merge_specific()
        elif choice == 3:
            self._list_mods()
        elif choice == 4:
            self._switch_mission()
        elif choice == 5:
            self._auto_detect()
        elif choice == 6:
            self._merge_settings()

    def action_opt_1(self) -> None:
        self._handle_xml_choice(1)

    def action_opt_2(self) -> None:
        self._handle_xml_choice(2)

    def action_opt_3(self) -> None:
        self._handle_xml_choice(3)

    def action_opt_4(self) -> None:
        self._handle_xml_choice(4)

    def action_opt_5(self) -> None:
        self._handle_xml_choice(5)

    def action_opt_6(self) -> None:
        self._handle_xml_choice(6)

    def _quick_merge(self) -> None:
        self._do_quick_merge()

    @work(thread=True)
    def _do_quick_merge(self) -> None:
        log = self.query_one("#xml-log", RichLog)
        writer = LogWriter(log, self.app)

        with redirect_stdout(writer), redirect_stderr(writer):
            self.app.call_from_thread(log.write, "Scanning for mods...")
            mods = self.merger.scan_for_mods()
            if not mods:
                self.app.call_from_thread(
                    log.write, "No mods found. Check mod_search_paths in merge_config.json"
                )
                return

            self.app.call_from_thread(log.write, f"Found {len(mods)} mod(s). Merging...")
            for mod in mods:
                self.merger.merge_mod(mod)
            self.app.call_from_thread(log.write, "\nAll mods merged!")

        self.app.call_from_thread(
            self.notify, "Quick merge complete!", severity="information"
        )

    def _merge_specific(self) -> None:
        mod_path = self.query_one("#xml-mod-path", Input).value.strip()
        if not mod_path or not os.path.isdir(mod_path):
            self.notify("Enter a valid mod folder path", severity="error")
            return
        self._do_merge_specific(mod_path)

    @work(thread=True)
    def _do_merge_specific(self, mod_path: str) -> None:
        log = self.query_one("#xml-log", RichLog)
        writer = LogWriter(log, self.app)
        with redirect_stdout(writer), redirect_stderr(writer):
            self.merger.merge_mod(mod_path)
        self.app.call_from_thread(
            self.notify, "Merge complete!", severity="information"
        )

    def _list_mods(self) -> None:
        log = self.query_one("#xml-log", RichLog)
        log.clear()
        log.write("Scanning for mods...")
        mods = self.merger.scan_for_mods()
        if not mods:
            log.write("No mods found.")
            return
        log.write(f"Found {len(mods)} mod(s):\n")
        for i, mod in enumerate(mods, 1):
            xml_files = self.merger.find_mod_xml_files(mod)
            log.write(f"  {i}. {os.path.basename(mod)}")
            if xml_files["types"]:
                log.write(f"     [types.xml] {len(xml_files['types'])} file(s)")
            if xml_files["events"]:
                log.write(f"     [events.xml] {len(xml_files['events'])} file(s)")
            if xml_files["spawnabletypes"]:
                log.write(f"     [spawnabletypes.xml] {len(xml_files['spawnabletypes'])} file(s)")
            if not any(xml_files.values()):
                log.write("     (no mergeable XML files)")

    def _switch_mission(self) -> None:
        log = self.query_one("#xml-log", RichLog)
        log.clear()
        missions = self.merger.list_missions()
        if not missions:
            log.write("No missions configured. Use auto-detect first.")
            return
        log.write("Configured missions:")
        active = self.merger.config.get("active_mission", "")
        for i, m in enumerate(missions, 1):
            tag = " <- ACTIVE" if m == active else ""
            log.write(f"  {i}. {m}{tag}")
        log.write("\nEnter a mission number in the mod path field and press [2] Merge Specific")
        log.write("to switch mission (or edit merge_config.json directly).")

    def _auto_detect(self) -> None:
        self._do_auto_detect()

    @work(thread=True)
    def _do_auto_detect(self) -> None:
        log = self.query_one("#xml-log", RichLog)
        writer = LogWriter(log, self.app)
        with redirect_stdout(writer), redirect_stderr(writer):
            self.merger.auto_configure_missions()
        self.app.call_from_thread(
            self.notify, "Auto-detection complete!", severity="information"
        )

    def _merge_settings(self) -> None:
        log = self.query_one("#xml-log", RichLog)
        log.clear()
        rules = self.merger.config["merge_rules"]
        log.write("Current merge settings:")
        log.write(f"  Overwrite existing: {rules['overwrite_existing']}")
        log.write(f"  Skip vanilla duplicates: {rules['skip_vanilla_duplicates']}")
        log.write(f"  Backups enabled: {self.merger.config['backup_enabled']}")
        log.write(f"  Backup folder: {self.merger.config['backup_folder']}")
        log.write("\nEdit merge_config.json to change these settings.")


# ─── Restore Screen ────────────────────────────────────────────────────────

import argparse as _argparse

class RestoreScreen(TEMSScreen):
    """Select a backup archive and restore it to a target directory."""

    BINDINGS = [
        Binding("enter", "do_restore", "Restore", show=True),
        Binding("escape", "go_back",   "Back",    show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config
        self._archives: list = []
        self._running = False

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Restore Backup", classes="section-title")
            yield Static(
                "Select a backup from the table, choose a destination, then press Enter.",
                classes="info-text",
            )
            yield DataTable(id="restore-table")
            yield Label("Restore destination:")
            yield Input(id="restore-dest", placeholder="leave blank for backup_dir/restore/")
            yield Static("  [Enter] Restore   [Esc] Back", classes="key-hint")
            yield RichLog(id="restore-log", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self._load_archives()

    def _load_archives(self) -> None:
        self._archives = list_backup_archives(self.config)
        table = self.query_one("#restore-table", DataTable)
        table.clear(columns=True)
        table.add_columns("#", "Archive", "Size", "Created")
        if not self._archives:
            log = self.query_one("#restore-log", RichLog)
            log.write("No backups found in backup directory.")
            log.write(f"Expected: {self.config.backup_dir}")
            return
        from datetime import datetime as _dt
        for i, arc in enumerate(self._archives, 1):
            size_mb = f"{arc.stat().st_size / (1024 * 1024):.1f} MB"
            created = _dt.fromtimestamp(arc.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            table.add_row(str(i), arc.name, size_mb, created, key=str(i))
        table.move_cursor(row=0)

    def action_do_restore(self) -> None:
        if self._running or not self._archives:
            return
        table = self.query_one("#restore-table", DataTable)
        row = table.cursor_row
        if row is None or row >= len(self._archives):
            self.notify("Select a backup first", severity="warning")
            return
        archive = self._archives[row]
        dest_str = self.query_one("#restore-dest", Input).value.strip()
        from pathlib import Path as _Path
        if dest_str:
            restore_dir = _Path(dest_str).expanduser()
        else:
            restore_dir = _Path(self.config.backup_dir) / "restore"
        self._running = True
        self._do_restore(archive, restore_dir)

    @work(thread=True)
    def _do_restore(self, archive, restore_dir) -> None:
        log = self.query_one("#restore-log", RichLog)
        writer = LogWriter(log, self.app)
        with redirect_stdout(writer), redirect_stderr(writer):
            try:
                restore_backup_archive(archive, restore_dir)
            except Exception as e:
                self.app.call_from_thread(log.write, f"Error: {e}")
        self.app.call_from_thread(self._finish)

    def _finish(self) -> None:
        self._running = False
        self.notify("Restore complete!", severity="information")


# ─── Conflicts Screen ───────────────────────────────────────────────────────

class ConflictsScreen(TEMSScreen):
    """Scan installed mods for PBO/key conflicts."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Mod Conflict Detection", classes="section-title")
            yield Static(
                "Scanning for duplicate PBO files, key files, and LGSM config duplicates.",
                classes="info-text",
            )
            yield Static("  [Esc] Back", classes="key-hint")
            yield RichLog(id="conflicts-log", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self._run()

    @work(thread=True)
    def _run(self) -> None:
        log = self.query_one("#conflicts-log", RichLog)
        writer = LogWriter(log, self.app)
        with redirect_stdout(writer), redirect_stderr(writer):
            try:
                cmd_conflicts(_argparse.Namespace(), self.config)
            except Exception as e:
                self.app.call_from_thread(log.write, f"Error: {e}")


# ─── Deps Screen ────────────────────────────────────────────────────────────

class DepsScreen(TEMSScreen):
    """Check mod.cpp requiredAddons against installed mods."""

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Dependency Checker", classes="section-title")
            yield Static(
                "Reads requiredAddons from each mod.cpp and checks against installed mods.",
                classes="info-text",
            )
            yield Static("  [Esc] Back", classes="key-hint")
            yield RichLog(id="deps-log", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self._run()

    @work(thread=True)
    def _run(self) -> None:
        log = self.query_one("#deps-log", RichLog)
        writer = LogWriter(log, self.app)
        with redirect_stdout(writer), redirect_stderr(writer):
            try:
                cmd_deps(_argparse.Namespace(), self.config)
            except Exception as e:
                self.app.call_from_thread(log.write, f"Error: {e}")


# ─── Monitor Screen ─────────────────────────────────────────────────────────

class MonitorScreen(TEMSScreen):
    """Display server process, memory, CPU and disk stats."""

    BINDINGS = [
        Binding("f5",    "refresh",  "Refresh", show=True),
        Binding("r",     "refresh",  "Refresh", show=False),
        Binding("escape","go_back",  "Back",    show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def compose(self) -> ComposeResult:
        yield TEMSHeader()
        with VerticalScroll(id="content-area"):
            yield Static("Server Monitor", classes="section-title")
            yield Static("  [F5 / r] Refresh   [Esc] Back", classes="key-hint")
            yield RichLog(id="monitor-log", wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self._run()

    def action_refresh(self) -> None:
        log = self.query_one("#monitor-log", RichLog)
        log.clear()
        self._run()

    @work(thread=True)
    def _run(self) -> None:
        log = self.query_one("#monitor-log", RichLog)
        writer = LogWriter(log, self.app)
        with redirect_stdout(writer), redirect_stderr(writer):
            try:
                cmd_monitor(_argparse.Namespace(), self.config)
            except Exception as e:
                self.app.call_from_thread(log.write, f"Error: {e}")


# ─── The App ────────────────────────────────────────────────────────────────


TIPH_STYLE = """
Screen { background: #1a1a2e; color: #e0e0e0; }
Header { display: none; }
Footer { background: #111122; color: #6688aa; }

.panel-title { color: #ff8c00; text-style: bold; margin-bottom: 1; }
.field-label { color: #888888; margin-bottom: 0; }
.field-value        { color: #e0e0e0;  text-style: bold; margin-bottom: 1; }
.field-value-orange { color: #ff8c00;  text-style: bold; margin-bottom: 1; }
.field-value-green  { color: #57f287;  text-style: bold; margin-bottom: 1; }
.field-value-red    { color: #ed4245;  text-style: bold; margin-bottom: 1; }
.field-value-dim    { color: #555577;  margin-bottom: 1; }
.divider { color: #2a2a4e; margin-bottom: 1; }

.panel        { border: solid #2a2a4e; padding: 1 2; background: #111122; }
.panel-orange { border: solid #ff8c00; padding: 1 2; background: #111122; }

#main-layout  { layout: vertical;   height: 100%; }
#main-top     { layout: horizontal; height: 1fr;  }
#status-panel { width: 36; margin: 1 0 1 1; }
#menu-panel   { margin: 1 1 1 1; width: 1fr; }
#log-panel    { margin: 0 1 1 1; height: 13; }

.menu-label { color: #e0e0e0; padding: 1 2; margin-bottom: 1; background: #1e1e38; border: solid #2a2a4e; }

.key-hint { color: #ff8c00; padding: 1 0; }

DataTable                      { background: #111122; color: #e0e0e0; height: 1fr; }
DataTable > .datatable--header { background: #1e1e38; color: #ff8c00; text-style: bold; }
DataTable > .datatable--cursor { background: #331f00; color: #ff8c00; }
DataTable > .datatable--hover  { background: #222244; }

RichLog {
    background: #0a0a18; color: #aaaaaa;
    border: round #2a2a4e; padding: 0 1; height: 1fr;
    scrollbar-color: #ff8c00; scrollbar-background: #111122;
}

Input          { background: #111122; border: tall #2a2a4e; color: #e0e0e0; margin: 1 0; }
Input:focus    { border: tall #ff8c00; }
Input.-invalid { border: tall #ed4245; }

RadioSet       { background: #1a1a2e; border: tall #333355; padding: 1 1; margin: 1 0; }
RadioSet:focus { border: tall #ff8c00; }
RadioButton    { background: #1a1a2e; padding: 0 1; }

ConfirmModal { align: center middle; }
#confirm-dialog {
    align: center middle; width: 56; height: auto;
    background: #1e1e38; border: thick #ed4245; padding: 2 3;
}
#confirm-dialog Static { width: 100%; text-align: center; margin: 1 0; }

#content-area  { padding: 1 2; height: 1fr; background: #1a1a2e; }
.section-title { color: #ff8c00; text-style: bold; padding: 1 0 0 0; }
.info-text     { color: #6688aa; padding: 0 0 1 0; }
.success-text  { color: #57f287; }
.error-text    { color: #ed4245; }
.warning-text  { color: #ccaa33; }
.form-group    { height: auto; padding: 0 0 1 0; }

ProgressBar     { padding: 1 0; }
ProgressBar Bar { color: #ff8c00; background: #333355; }

* {
    scrollbar-color: #333355;
    scrollbar-color-hover: #ff8c00;
    scrollbar-background: #111122;
}
"""

class TEMSApp(App):
    """TEMS Textual TUI Application."""

    CSS = TIPH_STYLE
    TITLE = "TEMS - Tsana Extended Management System"

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, config: Config) -> None:
        super().__init__()
        self.config = config

    def on_mount(self) -> None:
        self.push_screen(MainMenuScreen())


if __name__ == "__main__":
    config = Config()
    app = TEMSApp(config)
    app.run()
