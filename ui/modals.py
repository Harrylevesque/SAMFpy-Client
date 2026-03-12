"""Modal dialogs for SAMF.py client."""

from textual.app import ComposeResult
from textual.widgets import Button, Input, Label
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen


class RenameUsernameModal(ModalScreen):
    """Unskippable modal that forces the user to rename a CHANGEME username."""

    CSS = """
    RenameUsernameModal {
        align: center middle;
    }
    #rename-box {
        width: 60;
        height: auto;
        background: #161b22;
        border: solid #f0883e;
        padding: 2 4;
    }
    #rename-box Label {
        margin-bottom: 1;
    }
    #rename-title {
        color: #f0883e;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #rename-input {
        margin-bottom: 1;
    }
    #rename-confirm {
        width: 100%;
    }
    """

    def __init__(self, sv_uuid: str, svu_uuid: str, service_name: str):
        super().__init__()
        self._sv_uuid = sv_uuid
        self._svu_uuid = svu_uuid
        self._service_name = service_name

    def compose(self) -> ComposeResult:
        with Vertical(id="rename-box"):
            yield Label("⚠  Username Required", id="rename-title")
            yield Label(
                f"Your account [bold]{self._svu_uuid[:16]}…[/bold] on service\n"
                f"[cyan]{self._service_name}[/cyan]\n"
                f"still has the placeholder username [red]CHANGEME[/red].\n"
                f"Please enter a real username to continue."
            )
            yield Input(placeholder="Enter new username…", id="rename-input")
            yield Button("Confirm", id="rename-confirm", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "rename-confirm":
            new_name = self.query_one("#rename-input", Input).value.strip()
            if not new_name:
                self.query_one("#rename-input", Input).border_title = "Username cannot be empty!"
                return
            self.dismiss(new_name)

    def on_key(self, event) -> None:
        # Block Escape so the modal cannot be closed without entering a name
        if event.key == "escape":
            event.prevent_default()


class KillConnectionModal(ModalScreen):
    """Modal to confirm killing a connection."""

    CSS = """
    KillConnectionModal {
        align: center middle;
    }
    #kill-box {
        width: 60;
        height: auto;
        background: #161b22;
        border: solid #ff6b6b;
        padding: 2 4;
    }
    #kill-title {
        color: #ff6b6b;
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }
    #kill-buttons {
        height: auto;
        margin-top: 1;
    }
    """

    def __init__(self, con_filename: str):
        super().__init__()
        self._con_filename = con_filename

    def compose(self) -> ComposeResult:
        with Vertical(id="kill-box"):
            yield Label("⚠  Kill Connection", id="kill-title")
            yield Label(
                f"Are you sure you want to kill this connection?\n"
                f"[dim]{self._con_filename}[/dim]\n\n"
                f"[red]This action cannot be undone.[/red]"
            )
            with Horizontal(id="kill-buttons"):
                yield Button("Cancel", id="kill-cancel", variant="default")
                yield Button("Kill", id="kill-confirm", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "kill-confirm":
            self.dismiss(True)
        elif event.button.id == "kill-cancel":
            self.dismiss(False)

