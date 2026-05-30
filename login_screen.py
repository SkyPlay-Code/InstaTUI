# login_screen.py
from textual.screen import Screen
from textual.widgets import Input, Button, Label
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
            self.trigger_login()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("username", "password"):
            self.trigger_login()

    def trigger_login(self) -> None:
        # Check if already processing to avoid concurrent requests
        try:
            if self.query_one("#login-btn", Button).disabled:
                return
        except Exception:
            pass

        username = self.query_one("#username", Input).value
        password = self.query_one("#password", Input).value
        
        if username and password:
            self.set_loading_state(True)
            self.query_one("#status-msg", Label).update("Logging in... please wait.")
            self.run_login(username, password)
        else:
            self.query_one("#status-msg", Label).update("Please fill all fields!")

    def set_loading_state(self, loading: bool) -> None:
        """Enables or disables input elements and changes button state to prevent overlapping calls."""
        try:
            login_btn = self.query_one("#login-btn", Button)
            username_input = self.query_one("#username", Input)
            password_input = self.query_one("#password", Input)
            
            login_btn.disabled = loading
            username_input.disabled = loading
            password_input.disabled = loading
            
            if loading:
                login_btn.label = "Logging in... ⏳"
            else:
                login_btn.label = "Login"
        except Exception:
            pass

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
        self.set_loading_state(False)
        self.app.switch_screen("dashboard")

    def show_error(self, error_msg: str):
        self.set_loading_state(False)
        self.query_one("#status-msg", Label).update(f"❌ Error: {error_msg}")
