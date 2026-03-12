from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Input, Label
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from saving.userfiles import save_response_svu
from pathlib import Path
import json
import os


BASE_DIR = Path(__file__).resolve().parent
HUMANS_FILE = BASE_DIR / "humans.json"


def load_humans() -> dict:
    if HUMANS_FILE.exists():
        try:
            with open(HUMANS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_humans(humans: dict) -> None:
    tmp = str(HUMANS_FILE) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(humans, f, indent=2)
    os.replace(tmp, str(HUMANS_FILE))


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


class SAMFpy(App):
    CSS_PATH = "ui.css"

    status = reactive("Secure")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_page = "dashboard"

    def compose(self) -> ComposeResult:
        """Compose the main layout."""
        yield Header(show_clock=True)

        with Horizontal(id="body"):

            # Sidebar
            with Vertical(id="sidebar"):
                yield Static("SAMF.py Client Panel", classes="title")
                yield Button("Signup", id="signup", variant="success")
                yield Button("Login", id="login", variant="primary")
                # Connections button (shows current con--*.json entries)
                yield Button("Connections", id="connections", variant="warning")
                yield Button("Delete Account", id="delete", variant="error", classes="bottom_button")

            # Main panel (content swaps here)
            with Vertical(id="main_panel"):
                # Initial dashboard content
                yield Static("System Status", classes="section")
                yield Static("", id="status")

        yield Footer()

    # Helper to write logs — logs UI removed, so update status and print to stdout
    def write_log(self, message: str):
        """Previously wrote to an in-app Log widget; now update the status and print."""
        try:
            # Update the status so users still see recent activity in the UI
            self.update_status(message)
        except Exception:
            pass
        # Keep console output for debugging
        print(message)

    # Helper to update status
    def update_status(self, new_status: str = None):
        if new_status:
            self.status = new_status
        # Update the existing status widget rather than creating a new one
        try:
            status_widget = self.query_one("#status", Static)
            status_widget.update(f"[bold green]Status:[/] {self.status}")
        except Exception:
            # If for some reason the widget isn't available, ignore silently
            pass

    # Replace main panel content (defensive against DuplicateIds)
    def show_main_content(self, widgets):
        main_panel = self.query_one("#main_panel", Vertical)

        # Remove all children safely
        for child in list(main_panel.children):
            try:
                child.remove()
            except Exception:
                pass

        # Defensive: ensure that any incoming widget IDs don't collide with
        # existing registry entries (Textual can raise DuplicateIds if a
        # widget with the same id was not fully unregistered yet). Remove any
        # existing widgets with the same id before mounting.
        for w in widgets:
            try:
                wid = getattr(w, "id", None)
                if wid:
                    for existing in list(main_panel.query(f"#{wid}")):
                        try:
                            existing.remove()
                        except Exception:
                            pass
            except Exception:
                pass

        # Mount new widgets, but avoid remounting a widget that's already present
        for widget in widgets:
            try:
                if widget in main_panel.children:
                    continue
                main_panel.mount(widget)
            except Exception:
                # If mounting a specific widget fails, continue with others
                continue

    # Dashboard view
    def show_dashboard(self):
        # Reuse existing status widget to avoid duplicate IDs
        try:
            status_widget = self.query_one("#status", Static)
        except Exception:
            status_widget = Static(f"{self.status}")

        # Ensure status widget text is up to date
        status_widget.update(f"{self.status}")

        widgets: list = [
            Static("System Status", classes="section"),
            status_widget,
        ]
        self.show_main_content(widgets)

    # Signup form view
    def show_signup_form(self):
        # Create inputs without static IDs to avoid DuplicateIds when swapping views
        ip_input = Input(placeholder="Server IP (e.g. https://example.com)", value="https://")
        id_input = Input(placeholder="Server ID (service UUID)")
        submit_button = Button("Submit", id="submit_signup", variant="success")
        widgets: list = [
            Static("Signup Form", classes="title"),
            Static("Enter server details:", classes="section"),
            ip_input,
            id_input,
            submit_button,
        ]
        # Keep references to these inputs so the submit handler can read values
        self._signup_ip_widget = ip_input
        self._signup_id_widget = id_input
        self.show_main_content(widgets)

    # Connections view: connections page removed

    # Handle signup submit
    def handle_signup(self, server_ip: str, server_id: str):
        # Validate inputs
        server_ip = server_ip.strip() if server_ip else ""
        server_id = server_id.strip() if server_id else ""

        if not server_ip:
            self.write_log("[red]Server IP is required for signup")
            return
        if not server_id:
            self.write_log("[red]Server ID is required for signup")
            return

        self.write_log(f"[green]Signup submitted: IP={server_ip}, ID={server_id}")

        # Call the save function with provided server details. This will
        # generate keys, POST to the server and save the resulting SVU file.
        try:
            save_response_svu(serviceip_param=server_ip, service_uuid_param=server_id)
            self.write_log("[green]Signup completed; saved SVU data locally")
        except Exception as e:
            self.write_log(f"[red]Signup failed: {e}")

        # return to dashboard after submission
        self.show_dashboard()

    # Login page view
    def show_login_page(self):
        """Show the login page, but first handle any CHANGEME usernames."""
        self._changeme_queue = []  # list of (sv_uuid, svu_uuid, service_name)
        humans = load_humans()
        for sv_uuid, sv_data in humans.items():
            if not isinstance(sv_data, dict):
                continue
            service_name = sv_data.get("hrn") or sv_data.get("serviceip") or sv_uuid
            for key, val in sv_data.items():
                if key.startswith("svu--") and isinstance(val, dict):
                    if val.get("username") == "CHANGEME":
                        self._changeme_queue.append((sv_uuid, key, service_name))

        if self._changeme_queue:
            self._process_changeme_queue()
        else:
            self._render_login_page()

    def _process_changeme_queue(self):
        """Pop the first CHANGEME entry and show the rename modal."""
        if not self._changeme_queue:
            self._render_login_page()
            return
        sv_uuid, svu_uuid, service_name = self._changeme_queue[0]

        def on_rename(new_name: str):
            # Save the new name into humans.json
            humans = load_humans()
            svc = humans.get(sv_uuid, {})
            if svu_uuid in svc:
                svc[svu_uuid]["username"] = new_name
            humans[sv_uuid] = svc
            save_humans(humans)
            self.write_log(f"[green]Username updated to '{new_name}' for {svu_uuid[:16]}…")
            self._changeme_queue.pop(0)
            self._process_changeme_queue()

        self.push_screen(RenameUsernameModal(sv_uuid, svu_uuid, service_name), callback=on_rename)

    def _render_login_page(self):
        """Render the actual login selection page."""
        humans = load_humans()
        widgets: list = [
            Static("Login", classes="title"),
            Static("Select a service and account to log in:", classes="section"),
        ]

        if not humans:
            widgets.append(Static("[yellow]No services found in humans.json. Please sign up first."))
        else:
            for sv_uuid, sv_data in humans.items():
                if not isinstance(sv_data, dict):
                    continue
                service_name = sv_data.get("hrn") or sv_data.get("serviceip") or sv_uuid
                service_ip = sv_data.get("serviceip", "")
                widgets.append(Static(f"[bold cyan]{service_name}[/bold cyan]  [dim]{service_ip}[/dim]", classes="section"))
                svu_entries = [(k, v) for k, v in sv_data.items() if k.startswith("svu--") and isinstance(v, dict)]
                if not svu_entries:
                    widgets.append(Static("[dim]  No accounts for this service."))
                for svu_uuid, svu_data in svu_entries:
                    username = svu_data.get("username", "unknown")
                    btn = Button(
                        f"Login as {username}  [{svu_uuid[:16]}…]",
                        id=f"login__{sv_uuid}__{svu_uuid}",
                        variant="primary",
                    )
                    widgets.append(btn)

        self.show_main_content(widgets)

    def handle_login(self, sv_uuid: str, svu_uuid: str):
        """Trigger the login flow for the given sv/svu pair."""
        from login.processor import login_processor
        humans = load_humans()
        svc = humans.get(sv_uuid, {})
        service_ip = svc.get("serviceip", "")
        if not service_ip:
            self.write_log(f"[red]No service IP found for {sv_uuid}")
            return
        self.write_log(f"[yellow]Logging in as {svu_uuid[:16]}… on {service_ip}…")
        try:
            result = login_processor(sv_uuid, svu_uuid, service_ip)
            self.write_log(f"[green]Login result: {result}")
        except Exception as e:
            self.write_log(f"[red]Login failed: {e}")
        self.show_dashboard()

    # Button click events
    def on_button_pressed(self, event: Button.Pressed):
        button_id = event.button.id

        if button_id == "signup":
            self.show_signup_form()

        elif button_id == "login":
            self.show_login_page()

        elif button_id == "connections":
            # Connections button clicked (no action for now)
            self.write_log("[yellow]Connections feature coming soon")

        elif button_id and button_id.startswith("login__"):
            # Format: login__{sv_uuid}__{svu_uuid}
            parts = button_id.split("__", 2)
            if len(parts) == 3:
                self.handle_login(parts[1], parts[2])

        elif button_id == "delete":
            self.write_log("[red]Account deletion requested")

        elif button_id == "submit_signup":
            # Read values from stored widgets rather than querying by ID
            ip_widget = getattr(self, "_signup_ip_widget", None)
            id_widget = getattr(self, "_signup_id_widget", None)
            ip = ip_widget.value if ip_widget is not None else ""
            server_id = id_widget.value if id_widget is not None else ""
            self.handle_signup(ip, server_id)


    # Initial mount
    def on_mount(self):
        # Logs removed; use status updates and stdout for messages
        self.write_log("[bold green]SAMF.py Client Started")
        self.write_log("[dim]Waiting for user action...")
        self.show_dashboard()


if __name__ == "__main__":
    SAMFpy().run()
