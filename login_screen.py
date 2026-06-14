# login_screen.py
from textual.screen import Screen
from textual.widgets import Input, Button, Static, Label
from textual.containers import Vertical
from textual import work
from instagrapi.exceptions import ChallengeRequired, TwoFactorRequired 

class LoginScreen(Screen):
    """The Screen where users enter credentials and handle challenges natively."""

    def compose(self):
        with Vertical(id="login-form"):
            yield Label("INSTAGRAM TERMINAL", id="title")
            yield Input(placeholder="Username", id="username")
            yield Input(placeholder="Password", password=True, id="password")
            yield Button("Login", variant="primary", id="login-btn")
            
            # Resumes the login flow natively!
            yield Button("📱 I Approved It On My Phone (Resume)", variant="warning", id="resume-btn", disabled=True)
            
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
                
        elif event.button.id == "resume-btn":
            self.query_one("#status-msg", Label).update("Resuming login flow...")
            self.query_one("#resume-btn").disabled = True
            self.resume_login()

    @work(thread=True)
    def run_login(self, username, password):
        try:
            self.app.ig_client.login(username, password)
            self.app.ig_client.dump_settings("session.json")
            self.app.call_from_thread(self.go_to_dashboard)
            
        except TwoFactorRequired as e:
            self.app.call_from_thread(self.prompt_2fa_ui, username, password)
            
        except ChallengeRequired as e:
            # Native 2.10.8 ChallengeRequired
            self.app.call_from_thread(self.show_manual_approval_needed)
            
        except Exception as e:
            self.app.call_from_thread(self.show_error, str(e))

    def prompt_2fa_ui(self, username, password):
        self.query_one("#status-msg", Label).update("🔒 Two-Factor Required! Check your Authenticator / SMS.")
        
        def callback(code):
            if code:
                self.query_one("#status-msg", Label).update("Submitting 2FA code...")
                self.submit_2fa_login(username, password, code)
                
        from challenge_screen import ChallengeScreen
        self.app.push_screen(ChallengeScreen(), callback)

    @work(thread=True)
    def submit_2fa_login(self, username, password, code):
        try:
            self.app.ig_client.login(username, password, verification_code=code)
            self.app.ig_client.dump_settings("session.json")
            self.app.call_from_thread(self.go_to_dashboard)
        except Exception as e:
            self.app.call_from_thread(self.show_error, str(e))

    @work(thread=True)
    def resume_login(self):
        try:
            username = self.query_one("#username", Input).value
            password = self.query_one("#password", Input).value
            
            # CALLS THE NEW NATIVE METHOD!
            self.app.ig_client.challenge_bloks_redirect_dismiss()
            
            self.app.call_from_thread(self.query_one("#status-msg", Label).update, "Block lifted! Fetching new cookies...")
            self.app.ig_client.login(username, password)
            self.app.ig_client.dump_settings("session.json")
            self.app.call_from_thread(self.go_to_dashboard)
        except Exception as e:
            self.app.call_from_thread(self.show_error, f"Resume failed: {e}")

    def show_manual_approval_needed(self):
        self.query_one("#status-msg", Label).update("⚠️ Open Instagram app on phone, tap 'It was me', then click Resume.")
        self.query_one("#resume-btn").disabled = False
        self.query_one("#login-btn").disabled = True

    def go_to_dashboard(self):
        self.app.switch_screen("dashboard")

    def show_error(self, error_msg: str):
        safe_error = error_msg.replace("[", "\\[")
        self.query_one("#status-msg", Label).update(f"❌ Error: {safe_error}")
        self.query_one("#login-btn").disabled = False