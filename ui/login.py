"""Login screen for SAMF.py client."""

from textual.widgets import Button, Static


class LoginScreen:
    """Login selection screen."""

    @staticmethod
    def create_login_widgets(humans: dict):
        """Create login selection widgets."""
        widgets = [
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
                widgets.append(
                    Static(
                        f"[bold cyan]{service_name}[/bold cyan]  [dim]{service_ip}[/dim]",
                        classes="section",
                    )
                )
                svu_entries = [
                    (k, v) for k, v in sv_data.items() if k.startswith("svu--") and isinstance(v, dict)
                ]
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

        return widgets

