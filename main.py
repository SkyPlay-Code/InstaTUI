# main.py
import os
import time
import threading
from textual.app import App
from textual import work
# Reverted back to the official, standard Client!
from instagrapi import Client

from login_screen import LoginScreen
from dashboard_screen import DashboardScreen
from challenge_screen import ChallengeScreen

class InstaTermApp(App):
    """The Main App Controller."""

    BINDINGS = [
        ("q", "quit", "Quit App")
    ]

    SCREENS = {
        "login": LoginScreen,
        "dashboard": DashboardScreen
    }

    # Your existing CSS (Unchanged)
    CSS = """
    Screen { align: center middle; background: $background; }
    TabPane { padding: 1 2; align: center middle; }
    #login-form { width: 45; height: auto; border: thick $primary; padding: 2 4; background: $surface; }
    #title { text-align: center; width: 100%; text-style: bold; margin-bottom: 2; color: $accent; }
    Input { margin-bottom: 1; }
    Button { width: 100%; margin-top: 1; }
    #status-msg { text-align: center; width: 100%; color: yellow; margin-top: 1; }
    #inbox-container { width: 90%; height: 100%; border: solid $secondary; padding: 1; background: $surface; }
    #inbox-header { width: 100%; text-align: center; text-style: bold; padding-bottom: 1; border-bottom: solid $secondary; margin-bottom: 1; }
    OptionList { height: 1fr; border: blank; }
    #refresh-inbox-btn { margin-bottom: 1; }
    #chat-main-container { width: 80%; height: 90%; border: solid $secondary; padding: 1; background: $surface; }
    #chat-header { width: 100%; text-align: center; text-style: bold; padding-bottom: 1; border-bottom: solid $secondary; color: $accent; }
    #message-container { height: 1fr; border: round $primary; padding: 1; margin-top: 1; margin-bottom: 1; overflow-y: scroll; background: $background; }
    #input-container { height: 3; }
    #message-input { width: 1fr; }
    #send-btn { width: 15; margin-left: 1; }
    #back-btn { margin-top: 1; width: 100%; }
    .msg-me { color: $success; text-align: right; width: auto; max-width: 90%; padding: 0 1; }
    .msg-them { color: $warning; text-align: left; width: auto; max-width: 90%; padding: 0 1; }
    .msg-system { color: $error; text-align: center; text-style: italic; margin: 1 0; }
    #profile-search { margin-bottom: 1; }
    #profile-card { width: 100%; height: auto; border: solid $secondary; padding: 1; background: $surface; }
    #profile-top-section { height: auto; margin-bottom: 1; }
    #profile-pic-container { width: 36; height: auto; margin-right: 2; }
    #profile-stats-container { height: auto; align-vertical: middle; }
    #profile-username { margin-bottom: 1; }
    #profile-counters { color: $accent; }
    #profile-bio { margin-top: 1; border-top: solid $secondary; padding-top: 1; }
    #profile-actions { height: auto; margin-top: 1; border-top: solid $secondary; padding-top: 1; }
    #profile-actions Button { width: 1fr; margin: 0 1; }
    #network-container { width: 100%; height: 100%; border: solid $secondary; padding: 1; background: $surface; }
    #net-header { text-style: bold; text-align: center; width: 100%; margin-bottom: 1; color: $accent; }
    #net-sub { text-align: center; width: 100%; margin-bottom: 1; }
    #scan-btn { width: 100%; margin-bottom: 1; }
    #challenge-box { width: 50; height: auto; padding: 2; background: $surface; border: thick $error; align: center middle; }
    #challenge-title { text-align: center; text-style: bold; width: 100%; color: $error; margin-bottom: 1; }
    #challenge-desc { text-align: center; margin-bottom: 1; }
    """

    def __init__(self):
        super().__init__()
        # Standard native client (no overrides needed!)
        self.ig_client = Client()
        self.last_msg_id = None
        
        self.challenge_event = threading.Event()
        self.challenge_code = ""
        self.ig_client.challenge_code_handler = self.gui_challenge_handler

    def gui_challenge_handler(self, username: str, choice=None) -> str:
        self.challenge_event.clear()
        self.call_from_thread(self.trigger_challenge_ui)
        self.challenge_event.wait() 
        return self.challenge_code

    def trigger_challenge_ui(self):
        def callback(code):
            self.challenge_code = code
            self.challenge_event.set()
            self.notify("Code submitted. Waiting for Instagram...", severity="warning")

        self.push_screen(ChallengeScreen(), callback)

    def on_mount(self):
        self.set_interval(30, self.poll_notifications)
        
        if os.path.exists("session.json"):
            try:
                self.ig_client.load_settings("session.json")
                self.push_screen("dashboard")
            except Exception:
                self.push_screen("login")
        else:
            self.push_screen("login")

    @work(thread=True)
    def poll_notifications(self):
        if not getattr(self.ig_client, 'user_id', None):
            return 
        try:
            threads = self.ig_client.direct_threads(amount=1)
            if threads and threads[0].messages:
                latest_msg = threads[0].messages[0]
                if self.last_msg_id is None:
                    self.last_msg_id = latest_msg.id
                    return

                if latest_msg.id != self.last_msg_id:
                    self.last_msg_id = latest_msg.id
                    if str(latest_msg.user_id) != str(self.ig_client.user_id):
                        sender = threads[0].thread_title or "Someone"
                        text = latest_msg.text if latest_msg.text else "📷 Media"
                        self.app.call_from_thread(self.notify, text, title=f"New message from {sender}", severity="info")
        except Exception:
            pass

if __name__ == "__main__":
    try:
        app = InstaTermApp()
        app.run()
    except Exception as e:
        print(f"Application failed to start: {e}")