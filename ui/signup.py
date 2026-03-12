"""Signup screen for SAMF.py client."""

from textual.widgets import Button, Input, Static


class SignupScreen:
    """Signup form screen."""

    @staticmethod
    def create_signup_widgets():
        """Create signup form widgets."""
        ip_input = Input(placeholder="Server IP (e.g. https://example.com)")
        id_input = Input(placeholder="Server ID (service UUID)")
        submit_button = Button("Submit", id="submit_signup", variant="success")

        widgets = [
            Static("Signup Form", classes="title"),
            Static("Enter server details:", classes="section"),
            ip_input,
            id_input,
            submit_button,
        ]

        return widgets, ip_input, id_input

