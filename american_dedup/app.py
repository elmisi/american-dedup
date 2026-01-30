"""Main application for american-dedup."""

from textual.app import App
from textual.binding import Binding

from . import __version__
from .screens import MainSelectScreen, UndoScreen


class AmericanDedupApp(App):
    """TUI application for managing duplicate files using fdupes."""

    TITLE = f"american-dedup v{__version__}"
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Screen {
        background: $surface;
    }
    Header {
        dock: top;
    }
    Footer {
        dock: bottom;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("u", "undo", "Undo"),
        Binding("f1", "help", "Help"),
    ]

    def __init__(self, start_path: str = "/") -> None:
        """
        Initialize the application.

        Args:
            start_path: Initial path for the folder picker dialog.
        """
        super().__init__()
        self.start_path = start_path
        self.selected_folders: list[str] = []
        self.source_folders: list[str] = []
        self.include_internal: bool = False
        self.fdupes_output: str = ""
        self.analysis: dict = {}

    def on_mount(self) -> None:
        """Handle application mount event."""
        self.push_screen(MainSelectScreen(self.start_path))

    def action_undo(self) -> None:
        """Handle undo action."""
        self.push_screen(UndoScreen())

    def action_help(self) -> None:
        """Handle help action."""
        from .screens import HelpScreen
        self.push_screen(HelpScreen())


def main(start_path: str = "/") -> None:
    """
    Entry point for the application.

    Args:
        start_path: Initial path for the folder picker dialog.
    """
    app = AmericanDedupApp(start_path)
    app.run()


if __name__ == "__main__":
    main()
