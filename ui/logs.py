"""Logs screen for SAMF.py client."""

from textual.app import ComposeResult
from textual.widgets import Button, Static, Label
from textual.containers import Vertical
from textual.screen import Screen


class LogsScreen(Screen):
    """Screen to display logs for a connection."""

    CSS = """
    LogsScreen {
        layout: vertical;
    }
    #logs-header {
        height: auto;
        background: #0d1117;
        border-bottom: solid #30363d;
        padding: 1 2;
    }
    #logs-title {
        color: #58a6ff;
        text-style: bold;
        margin-bottom: 1;
    }
    #logs-content {
        height: 1fr;
        background: #0d1117;
        border: solid #30363d;
        padding: 1 2;
    }
    #logs-footer {
        height: auto;
        background: #0d1117;
        border-top: solid #30363d;
        padding: 1 2;
    }
    """

    def __init__(self, con_filename: str, con_data: dict):
        super().__init__()
        self._con_filename = con_filename
        self._con_data = con_data
        self._logs = []

    def compose(self) -> ComposeResult:
        with Vertical():
            with Vertical(id="logs-header"):
                yield Label(f"Logs: {self._con_filename}", id="logs-title")
                yield Static(
                    f"[dim]Connection UUID:[/dim] {self._con_data.get('con_uuid', 'N/A')}\n"
                    f"[dim]Service:[/dim] {self._con_data.get('sv_uuid', 'N/A')}\n"
                    f"[dim]User:[/dim] {self._con_data.get('svu_uuid', 'N/A')}"
                )
            with Vertical(id="logs-content"):
                yield Static("[yellow]Logs will be displayed here[/yellow]", id="logs-display")
            with Vertical(id="logs-footer"):
                yield Button("Back", id="logs-back", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "logs-back":
            self.app.pop_screen()

