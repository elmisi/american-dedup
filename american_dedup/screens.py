"""TUI screens for american-dedup."""

import asyncio
import concurrent.futures
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Checkbox,
    DirectoryTree,
    Footer,
    Header,
    Input,
    ListItem,
    ListView,
    ProgressBar,
    Static,
    Tree,
)


class FolderPickerModal(ModalScreen[str | None]):
    """Modal dialog for selecting a folder from the filesystem."""

    CSS = """
    FolderPickerModal {
        align: center middle;
    }
    #modal-dialog {
        width: 80%;
        height: 80%;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    #modal-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #path-input {
        margin-bottom: 1;
    }
    #dir-tree {
        height: 1fr;
        border: solid $secondary;
    }
    #modal-buttons {
        margin-top: 1;
        height: 3;
        align: center middle;
    }
    #modal-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, initial_path: str = "/") -> None:
        """
        Initialize the folder picker.

        Args:
            initial_path: Starting path for the directory tree.
        """
        super().__init__()
        self.initial_path = initial_path
        self.current_path = initial_path

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="modal-dialog"):
            yield Static("Select Folder", id="modal-title")
            yield Input(value=self.initial_path, id="path-input")
            yield DirectoryTree(self.initial_path, id="dir-tree")
            with Horizontal(id="modal-buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Select", id="select", variant="success")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle path input submission."""
        path = event.value
        if Path(path).is_dir():
            self.current_path = path
            tree = self.query_one("#dir-tree", DirectoryTree)
            tree.path = path

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Handle directory selection in tree."""
        self.current_path = str(event.path)
        self.query_one("#path-input", Input).value = self.current_path

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "select":
            self.dismiss(self.current_path)


class MainSelectScreen(Screen):
    """Main screen for selecting scan and target folders."""

    CSS = """
    #main-container {
        height: 1fr;
        margin: 1;
    }
    .folder-box {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        margin: 0 1;
        padding: 1;
    }
    .box-title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #scan-list, #target-list {
        height: 1fr;
        border: solid $secondary;
        margin: 1 0;
    }
    .folder-item {
        padding: 0 1;
    }
    .folder-item.selected {
        background: $accent;
    }
    .box-buttons {
        height: 3;
        align: center middle;
    }
    .box-buttons Button {
        margin: 0 1;
    }
    #info-text {
        text-align: center;
        margin: 1;
        color: $text-muted;
    }
    #bottom-buttons {
        height: auto;
        align: center middle;
        margin: 1 1 2 1;
        padding: 1;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, initial_path: str = "/") -> None:
        """
        Initialize the main selection screen.

        Args:
            initial_path: Starting path for folder picker dialogs.
        """
        super().__init__()
        self.initial_path = initial_path
        self.scan_folders: list[str] = []
        self.target_folders: set[str] = set()
        self.selected_index: int | None = None
        self.include_internal: bool = False

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        with Horizontal(id="main-container"):
            with Container(id="scan-box", classes="folder-box"):
                yield Static("Folders to Scan", classes="box-title")
                yield VerticalScroll(id="scan-list")
                with Horizontal(classes="box-buttons"):
                    yield Button("+ Add", id="add-scan")
                    yield Button("- Remove", id="remove-scan")

            with Container(id="target-box", classes="folder-box"):
                yield Static("Target Folders (duplicates moved)", classes="box-title")
                yield VerticalScroll(id="target-list")

        yield Static(
            "Duplicates in target folders will be MOVED.\n"
            "Files in other folders will be KEPT.",
            id="info-text",
        )
        yield Checkbox(
            "Include duplicates within target folders",
            id="include-internal-cb",
        )
        with Horizontal(id="bottom-buttons"):
            yield Button("Load Config", id="load-config")
            yield Button("Save Config", id="save-config")
            yield Button("Scan", id="scan-btn", variant="success", disabled=True)
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events."""
        if event.button.id == "add-scan":
            self.app.push_screen(
                FolderPickerModal(self.initial_path),
                callback=self._on_folder_selected,
            )
        elif event.button.id == "remove-scan":
            self._remove_selected_folder()
        elif event.button.id == "load-config":
            self.app.push_screen(LoadConfigScreen(), callback=self._on_config_loaded)
        elif event.button.id == "save-config":
            if self.scan_folders:
                self.app.push_screen(
                    SaveConfigScreen(
                        self.scan_folders,
                        list(self.target_folders),
                        self.include_internal,
                    )
                )
        elif event.button.id == "scan-btn":
            if self.scan_folders and self.target_folders:
                self.app.selected_folders = self.scan_folders.copy()
                self.app.source_folders = list(self.target_folders)
                self.app.include_internal = self.include_internal
                self.app.push_screen(ScanScreen())

    def _on_folder_selected(self, path: str | None) -> None:
        """Handle folder selection from picker."""
        if path and path not in self.scan_folders:
            self.scan_folders.append(path)
            self._refresh_lists()
            self._update_scan_button()

    def _on_config_loaded(
        self, result: tuple[list[str], list[str], bool] | None
    ) -> None:
        """Handle configuration load callback."""
        if result:
            folders, sources, include_internal = result
            self.scan_folders = folders
            self.target_folders = set(sources)
            self.include_internal = include_internal
            cb = self.query_one("#include-internal-cb", Checkbox)
            cb.value = include_internal
            self._refresh_lists()
            self._update_scan_button()

    def _remove_selected_folder(self) -> None:
        """Remove the currently selected folder."""
        if (
            self.selected_index is not None
            and 0 <= self.selected_index < len(self.scan_folders)
        ):
            folder = self.scan_folders.pop(self.selected_index)
            self.target_folders.discard(folder)
            self.selected_index = None
            self._refresh_lists()
            self._update_scan_button()

    def _refresh_lists(self) -> None:
        """Refresh the folder lists display."""
        scan_list = self.query_one("#scan-list", VerticalScroll)
        for child in list(scan_list.children):
            child.remove()

        for i, folder in enumerate(self.scan_folders):
            item = Static(f"  {folder}", classes="folder-item")
            if i == self.selected_index:
                item.add_class("selected")
            scan_list.mount(item)

        target_list = self.query_one("#target-list", VerticalScroll)
        for child in list(target_list.children):
            child.remove()

        for folder in self.scan_folders:
            cb = Checkbox(folder, value=(folder in self.target_folders))
            target_list.mount(cb)

    def _update_scan_button(self) -> None:
        """Update the scan button enabled state."""
        btn = self.query_one("#scan-btn", Button)
        btn.disabled = not (self.scan_folders and self.target_folders)

    def on_static_click(self, event) -> None:
        """Handle click on folder item."""
        widget = event.widget
        if widget.has_class("folder-item"):
            label = widget.renderable.plain.strip()
            try:
                self.selected_index = self.scan_folders.index(label)
                self._refresh_lists()
            except ValueError:
                pass

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state change."""
        if event.checkbox.id == "include-internal-cb":
            self.include_internal = event.value
            return

        label = str(event.checkbox.label)
        if event.value:
            self.target_folders.add(label)
        else:
            self.target_folders.discard(label)
        self._update_scan_button()


class ScanScreen(Screen):
    """Screen for running fdupes scan."""

    CSS = """
    #status {
        margin: 2;
        text-align: center;
    }
    #progress-container {
        margin: 2 4;
    }
    #progress-bar {
        margin: 0 2;
    }
    #progress-label {
        margin: 1 2;
        text-align: center;
    }
    #output {
        height: 1fr;
        margin: 1;
        border: solid gray;
        overflow-y: auto;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        from textual.widgets import ProgressBar

        yield Header()
        yield Static("Scanning...", id="status")
        with Container(id="progress-container"):
            yield ProgressBar(id="progress-bar", show_eta=False, total=100)
            yield Static("Initializing...", id="progress-label")
        yield VerticalScroll(id="output")
        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount."""
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
        self.fdupes_output = ""
        self.scan_done = False

        # Start fdupes directly
        self.logger.info("Starting fdupes scan...")
        self.run_worker(self._run_fdupes, thread=True)

    def on_worker_state_changed(self, event) -> None:
        """Handle worker state changes."""
        from .core import analyze_duplicates

        if event.state.name == "SUCCESS":
            result = event.worker.result

            if isinstance(result, str):
                # run_fdupes completed
                self.logger.info(f"run_fdupes completed, output length: {len(result)}")
                self.fdupes_output = result
                self.scan_done = True

                status = self.query_one("#status", Static)
                output = self.query_one("#output", VerticalScroll)
                progress_bar = self.query_one("#progress-bar")
                progress_label = self.query_one("#progress-label", Static)

                elapsed = int(time.time() - self.start_time)
                progress_bar.update(total=100, progress=100)
                progress_label.update(f"Completed in {elapsed}s")
                output.mount(Static(f"Scan completed in {elapsed}s"))

                status.update("Analyzing results...")
                self.app.fdupes_output = self.fdupes_output
                self.logger.info("Starting analyze_duplicates worker...")
                self.run_worker(self._analyze, thread=True)

            elif isinstance(result, dict):
                # analyze_duplicates completed
                self.logger.info(
                    f"analyze_duplicates completed, groups: {result.get('groups', 0)}"
                )
                self.app.analysis = result
                self.app.push_screen(PreviewScreen())

    def _run_fdupes(self) -> str:
        """Worker: run fdupes command."""
        from .core import run_fdupes

        self.logger.info("=== START _run_fdupes worker ===")

        def progress_callback(message: str, percentage: int):
            """Handle progress updates from fdupes."""
            self.app.call_from_thread(self._update_progress, message, percentage)

        result = run_fdupes(self.app.selected_folders, progress_callback)
        self.logger.info(f"=== END _run_fdupes worker, output: {len(result)} chars ===")
        return result

    def _update_progress(self, message: str, percentage: int) -> None:
        """Update progress bar and label."""
        if self.scan_done:
            return

        elapsed = int(time.time() - self.start_time)
        progress_bar = self.query_one("#progress-bar")
        progress_label = self.query_one("#progress-label", Static)

        if percentage < 0:
            # Indeterminate progress (building file list)
            progress_bar.update(total=None)  # Indeterminate mode
            progress_label.update(f"{message} - {elapsed}s")
        else:
            # Determinate progress (comparing files)
            progress_bar.update(total=100, progress=percentage)
            progress_label.update(f"{message} - {elapsed}s")

    def _analyze(self) -> dict:
        """Worker: analyze duplicates."""
        from .core import analyze_duplicates

        self.logger.info("=== START _analyze worker ===")
        include_internal = getattr(self.app, "include_internal", False)
        result = analyze_duplicates(
            self.fdupes_output,
            self.app.source_folders,
            include_internal,
        )
        self.logger.info(f"=== END _analyze worker, groups: {result.get('groups', 0)} ===")
        return result


class PreviewScreen(Screen):
    """Screen for previewing files to be moved."""

    CSS = """
    #summary {
        margin: 1;
        padding: 1;
        background: $surface;
        border: solid green;
    }
    #dup-tree {
        height: 1fr;
        margin: 1;
        border: solid blue;
    }
    .to-move {
        color: $warning;
    }
    .kept {
        color: $success;
    }
    #buttons {
        dock: bottom;
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Static(id="summary")
        yield Tree("Duplicates Found", id="dup-tree")
        yield Horizontal(
            Button("Back", id="back-btn"),
            Button("Execute Move", id="execute-btn", variant="warning"),
            id="buttons",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount."""
        from .core import format_size

        analysis = self.app.analysis
        summary = self.query_one("#summary", Static)
        summary.update(
            f"Duplicate groups: {analysis['groups']}\n"
            f"Files to move: {len(analysis['files_to_move'])}\n"
            f"Space to free: {format_size(analysis['total_size'])}\n\n"
            "🔴 = file to MOVE (target)  |  🟢 = file to KEEP"
        )

        tree = self.query_one("#dup-tree", Tree)
        tree.root.expand()

        # Group by folder
        by_folder: dict[str, list] = {}
        for dup in analysis.get("duplicates", []):
            to_move = dup["to_move"]
            parts = Path(to_move).parts
            if len(parts) > 4:
                top = str(Path(*parts[:5]))
            else:
                top = str(Path(to_move).parent)

            if top not in by_folder:
                by_folder[top] = []
            by_folder[top].append(dup)

        # Build tree
        for folder in sorted(by_folder.keys()):
            dups = by_folder[folder]
            total_size = sum(d["size"] for d in dups)
            folder_node = tree.root.add(
                f"📁 {folder} ({len(dups)} files, {format_size(total_size)})"
            )

            for dup in dups[:50]:  # Limit to 50 per folder for performance
                to_move = dup["to_move"]
                kept = dup["kept"]
                size = format_size(dup["size"])

                filename = Path(to_move).name

                dup_node = folder_node.add(f"📄 {filename} ({size})")
                dup_node.add_leaf(f"🔴 MOVE: {to_move}")
                dup_node.add_leaf(f"🟢 KEEP: {kept}")

            if len(dups) > 50:
                folder_node.add_leaf(f"... and {len(dups) - 50} more files")

        # Focus tree for arrow key navigation
        tree.focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "back-btn":
            self.app.pop_screen()
        elif event.button.id == "execute-btn":
            self.app.push_screen(ExecuteScreen())


class ExecuteScreen(Screen):
    """Screen for executing the move operation."""

    CSS = """
    #status {
        margin: 2;
        text-align: center;
    }
    #progress {
        margin: 2 4;
    }
    #current {
        margin: 1;
        text-align: center;
        color: gray;
    }
    #result {
        margin: 2;
        padding: 1;
        border: solid green;
    }
    #buttons {
        dock: bottom;
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Static("Moving files...", id="status")
        yield ProgressBar(id="progress")
        yield Static("", id="current")
        yield Static("", id="result")
        yield Horizontal(
            Button("Close", id="close-btn", variant="primary", disabled=True),
            id="buttons",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount."""
        self._run_move()

    def _run_move(self) -> None:
        """Execute the move operation."""
        from .config import save_undo_info
        from .core import execute_move

        async def do_move():
            status = self.query_one("#status", Static)
            progress = self.query_one("#progress", ProgressBar)
            current = self.query_one("#current", Static)
            result = self.query_one("#result", Static)
            close_btn = self.query_one("#close-btn", Button)

            analysis = self.app.analysis
            files = analysis["files_to_move"]
            progress.update(total=len(files), progress=0)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_path = str(Path(self.app.selected_folders[0]).parent)
            dest_dir = f"{base_path}/__dup_{timestamp}"

            def on_progress(i: int, total: int, path: str):
                progress.update(progress=i)
                current.update(Path(path).name[:60])

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    execute_move,
                    files,
                    dest_dir,
                    self.app.source_folders,
                    on_progress,
                )
                while not future.done():
                    await asyncio.sleep(0.05)
                result_data = future.result()

            save_undo_info(result_data["moves"], dest_dir)

            stats = result_data["stats"]
            status.update("Completed!")
            result.update(
                f"Moved: {stats['success']}\n"
                f"Skipped: {stats['skipped']}\n"
                f"Not found: {stats['not_found']}\n"
                f"Errors: {stats['error']}\n\n"
                f"Destination: {dest_dir}"
            )
            close_btn.disabled = False

        asyncio.create_task(do_move())

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close-btn":
            self.app.exit()


class UndoScreen(Screen):
    """Screen for undoing the last move operation."""

    CSS = """
    #info {
        margin: 2;
        padding: 1;
        border: solid yellow;
    }
    #progress {
        margin: 2 4;
    }
    #result {
        margin: 2;
    }
    #buttons {
        dock: bottom;
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Static("", id="info")
        yield ProgressBar(id="progress")
        yield Static("", id="result")
        yield Horizontal(
            Button("Cancel", id="cancel-btn"),
            Button("Restore", id="undo-btn", variant="warning"),
            id="buttons",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Handle screen mount."""
        from .config import load_undo_info

        info = self.query_one("#info", Static)
        undo_info = load_undo_info()

        if not undo_info:
            info.update("No move operation to undo.")
            self.query_one("#undo-btn", Button).disabled = True
        else:
            moves = undo_info.get("moves", [])
            dest = undo_info.get("dest_dir", "")
            info.update(
                f"Last move operation:\n"
                f"  Files: {len(moves)}\n"
                f"  Folder: {dest}"
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "undo-btn":
            self._run_undo()

    def _run_undo(self) -> None:
        """Execute the undo operation."""
        from .config import clear_undo_info, load_undo_info
        from .core import undo_move

        async def do_undo():
            progress = self.query_one("#progress", ProgressBar)
            result = self.query_one("#result", Static)
            undo_btn = self.query_one("#undo-btn", Button)
            cancel_btn = self.query_one("#cancel-btn", Button)

            undo_btn.disabled = True
            undo_info = load_undo_info()
            moves = undo_info.get("moves", [])
            progress.update(total=len(moves), progress=0)

            def on_progress(i: int, total: int, path: str):
                progress.update(progress=i)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(undo_move, undo_info, on_progress)
                while not future.done():
                    await asyncio.sleep(0.05)
                stats = future.result()

            clear_undo_info()
            result.update(
                f"Restored: {stats['success']}\n" f"Errors: {stats['error']}"
            )
            cancel_btn.label = "Close"

        asyncio.create_task(do_undo())


class LoadConfigScreen(ModalScreen[tuple[list[str], list[str], bool] | None]):
    """Modal screen for loading a saved configuration."""

    CSS = """
    LoadConfigScreen {
        align: center middle;
    }
    #config-dialog {
        width: 60%;
        height: 60%;
        border: solid $primary;
        background: $surface;
        padding: 1;
    }
    #title {
        text-align: center;
        text-style: bold;
        margin-bottom: 1;
    }
    #config-list {
        height: 1fr;
        margin: 1;
        border: solid blue;
    }
    #buttons {
        margin-top: 1;
        height: 3;
        align: center middle;
    }
    """

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="config-dialog"):
            yield Static("Saved Configurations:", id="title")
            yield ListView(id="config-list")
            yield Horizontal(
                Button("Cancel", id="cancel-btn"),
                id="buttons",
            )

    def on_mount(self) -> None:
        """Handle screen mount."""
        from .config import load_saved_configs

        self.configs = load_saved_configs()
        list_view = self.query_one("#config-list", ListView)

        if not self.configs:
            list_view.append(ListItem(Static("No saved configurations")))
        else:
            for name, data in self.configs.items():
                folders = len(data.get("folders", []))
                sources = len(data.get("sources", []))
                list_view.append(
                    ListItem(Static(f"{name} ({folders} folders, {sources} targets)"))
                )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-btn":
            self.dismiss(None)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle configuration selection."""
        if not self.configs:
            return

        name = list(self.configs.keys())[event.list_view.index]
        data = self.configs[name]

        folders = data.get("folders", [])
        sources = data.get("sources", [])
        include_internal = data.get("include_internal", False)
        self.dismiss((folders, sources, include_internal))


class SaveConfigScreen(Screen):
    """Screen for saving a configuration."""

    CSS = """
    #input-container {
        margin: 2;
    }
    #buttons {
        dock: bottom;
        height: auto;
        align: center middle;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        folders: list[str],
        sources: list[str],
        include_internal: bool = False,
    ) -> None:
        """
        Initialize the save config screen.

        Args:
            folders: List of folders to scan.
            sources: List of target folders.
            include_internal: Whether to include internal duplicates.
        """
        super().__init__()
        self.folders = folders
        self.sources = sources
        self.include_internal = include_internal

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield Container(
            Static("Configuration name:"),
            Input(placeholder="e.g. backup_drive", id="name-input"),
            id="input-container",
        )
        yield Horizontal(
            Button("Cancel", id="cancel-btn"),
            Button("Save", id="save-btn", variant="success"),
            id="buttons",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "save-btn":
            from .config import save_config

            name = self.query_one("#name-input", Input).value
            if name:
                save_config(name, self.folders, self.sources, self.include_internal)
                self.app.pop_screen()
