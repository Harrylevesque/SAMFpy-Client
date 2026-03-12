"""Connections screen for SAMF.py client."""
from textual.widgets import Static
class ConnectionsScreen:
    """Connections management screen."""
    @staticmethod
    def create_connections_widgets():
        """Create connections screen widgets."""
        widgets = [
            Static("Connections", classes="title"),
            Static("Connection management coming soon", classes="section"),
        ]
        return widgets
