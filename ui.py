from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static, Button, Input, Label
# Robust ScrollView import: different Textual versions export it differently.
try:
    # Preferred location in some versions
    from textual.widgets import ScrollView
except Exception:
    try:
        from textual.widgets.scroll_view import ScrollView
    except Exception:
        try:
            from textual.widgets.scrollview import ScrollView
        except Exception:
            ScrollView = None
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
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


class SAMFpy(App):
    CSS_PATH = "ui.css"

    status = reactive("Secure")

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
        ip_input = Input(placeholder="Server IP (e.g. https://example.com)")
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

    # Connections view: list con-*.json in storage/workingfiles and map to humans.json
    def show_connections_page(self):
        wf_dir = BASE_DIR / "storage" / "workingfiles"
        widgets: list = [
            Static("Current Connections", classes="title"),
            Static("Connections found in storage/workingfiles:", classes="section"),
        ]

        try:
            con_files = sorted(wf_dir.glob("con--*.json"))
        except Exception as e:
            widgets.append(Static(f"[red]Could not read workingfiles directory: {e}"))
            self.show_main_content(widgets)
            return

        if not con_files:
            widgets.append(Static("[dim]No connection files found."))
            self.show_main_content(widgets)
            return

        humans = load_humans()

        # Use a ScrollView if available; otherwise fall back to simple pagination
        use_scrollview = ScrollView is not None
        scroll = ScrollView(id="connections_scroll") if use_scrollview else None
        conn_children = []

        for p in con_files:
            data = None
            try:
                with open(p, "r") as f:
                    data = json.load(f)
            except Exception:
                # If parsing fails, add a placeholder button that identifies the file
                try:
                    placeholder = Button(f"[invalid] {p.name}", id=f"conn__{p.name}", variant="warning")
                    conn_children.append(placeholder)
                except Exception:
                    widgets.append(Static(f"[red]Failed to parse {p.name}"))
                continue

            # Some connection files were saved as a JSON array; normalize to a dict
            if isinstance(data, list):
                # Prefer the first dict that contains connection keys
                found = None
                for item in data:
                    if isinstance(item, dict) and ("sv_uuid" in item or "svu_uuid" in item or "con_uuid" in item):
                        found = item
                        break
                if found is None:
                    # Fallback: take the first element if it's a dict
                    if data and isinstance(data[0], dict):
                        data = data[0]
                    else:
                        widgets.append(Static(f"[red]Unexpected JSON structure in {p.name}"))
                        continue
                else:
                    data = found

            sv_uuid = data.get("sv_uuid")
            svu_uuid = data.get("svu_uuid")

            service_name = sv_uuid or "unknown-service"
            username = svu_uuid or "unknown-user"

            if sv_uuid and isinstance(humans, dict):
                svc = humans.get(sv_uuid, {}) if isinstance(humans, dict) else {}
                service_name = svc.get("hrn") or svc.get("serviceip") or service_name
                if svu_uuid and isinstance(svc, dict):
                    svu = svc.get(svu_uuid, {})
                    if isinstance(svu, dict):
                        username = svu.get("username", username)

            # Present as: username — service_name
            # Make each connection a button (currently a no-op when pressed)
            # Use the filename as a safe identifier; prefix to avoid collisions
            btn_id = f"conn__{p.name}"
            btn_label = f"{username}  —  {service_name}  [{p.name}]"
            try:
                # Add compact class so these buttons are visually smaller
                btn = Button(btn_label, id=btn_id, variant="warning", classes=("conn-button",))
                conn_children.append(btn)
            except Exception:
                # Fallback to a simple label if Button instantiation fails
                conn_children.append(Static(f"[bold]{username}[/bold]  —  [cyan]{service_name}[/cyan]  [dim]{p.name}[/dim]"))

        # If ScrollView available, mount the collected children into a Vertical
        # and mount that into the scroll view. Otherwise use pagination.
        try:
            if use_scrollview:
                list_container = Vertical(*conn_children, id="connections_list")
                scroll.mount(list_container)
                widgets.append(scroll)
            else:
                # Pagination fallback: store items on the instance and render a page
                self._conn_items = conn_children
                self._conn_page = getattr(self, "_conn_page", 0)
                page_size = 12
                start = self._conn_page * page_size
                end = start + page_size
                page_items = self._conn_items[start:end]

                # Add page items to widgets
                widgets.extend(page_items)

                # Prev / Next controls
                nav = []
                if self._conn_page > 0:
                    nav.append(Button("Previous", id="conn_prev", variant="default"))
                if end < len(self._conn_items):
                    nav.append(Button("Next", id="conn_next", variant="default"))
                if nav:
                    nav_container = Horizontal(*nav)
                    widgets.append(nav_container)
        except Exception:
            # Fallback: if anything goes wrong, extend widgets with the children
            widgets.extend(conn_children)
        # Debug: print summary of created connection widgets for diagnostic
        try:
            ids = [getattr(c, 'id', type(c).__name__) for c in conn_children]
            print(f"[debug]Connections built: {len(conn_children)}, ids={ids}, use_scrollview={use_scrollview}")
        except Exception:
            pass
        self.show_main_content(widgets)

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
            self.show_connections_page()

        elif button_id and button_id.startswith("conn__"):
            # Connection buttons are currently intentionally no-ops. Consume
            # the event so clicks don't fall through to other handlers.
            return

        elif button_id == "conn_prev":
            # Pagination: go to previous page
            if hasattr(self, "_conn_page") and self._conn_page > 0:
                self._conn_page -= 1
            self.show_connections_page()
            return

        elif button_id == "conn_next":
            # Pagination: go to next page
            if hasattr(self, "_conn_items"):
                page_size = 12
                max_page = (len(self._conn_items) - 1) // page_size
                if getattr(self, "_conn_page", 0) < max_page:
                    self._conn_page = getattr(self, "_conn_page", 0) + 1
            self.show_connections_page()
            return

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

        elif button_id == "back_to_tree":
            # Manage tab removed; just go back to dashboard
            try:
                self.show_dashboard()
            except Exception as e:
                self.write_log(f"[red]Could not return to dashboard: {e}")

    # Initial mount
    def on_mount(self):
        # Logs removed; use status updates and stdout for messages
        self.write_log("[bold green]SAMF.py Client Started")
        self.write_log("[dim]Waiting for user action...")
        self.show_dashboard()


if __name__ == "__main__":
    SAMFpy().run()
