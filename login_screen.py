# login_screen.py
from textual.screen import Screen
from textual.widgets import Input, Button, Static, Label
from textual.containers import Vertical
from textual import work

class LoginScreen(Screen):
    """The Screen where users enter credentials."""

    def compose(self):
        with Vertical(id="login-form"):
            yield Label("INSTAGRAM TERMINAL", id="title")
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Password", password=True, id="password")
            yield Button("Login", variant="primary", id="login-btn")
            yield Label("Ready.", id="status-msg")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "login-btn":
            username = self.query_one("#username", Input).value
            password = self.query_one("#password", Input).value
            
            if username and password:
                self.query_one("#status-msg", Label).update("Logging in... please wait.")
                self.run_login(username, password)
            else:
                self.query_one("#status-msg", Label).update("Please fill all fields!")

    @work(thread=True)
    def run_login(self, username, password):
        """Runs the login request in a background thread."""
        try:
            # self.app accesses the main InstaTermApp
            self.app.ig_client.login(username, password)
            self.app.ig_client.dump_settings("session.json")
            
            # Use call_from_thread to safely update UI from a background thread
            self.app.call_from_thread(self.go_to_inbox)
        except Exception as e:
            self.app.call_from_thread(self.show_error, str(e))

    def go_to_inbox(self):
        """Switches to the main dashboard."""
        self.app.switch_screen("dashboard")

    def show_error(self, error_msg: str):
        self.query_one("#status-msg", Label).update(f"❌ Error: {error_msg}")
