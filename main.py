# main.py
import os
from textual.app import App
from textual import work
from instagrapi import Client

from login_screen import LoginScreen
from dashboard_screen import DashboardScreen

class InstaTermApp(App):
    """The Main App Controller."""

    BINDINGS = [
        ("q", "quit", "Quit App")
    ]

    SCREENS = {
        "login": LoginScreen,
        "dashboard": DashboardScreen
    }

    # Your existing CSS
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
    #net-actions { height: auto; margin-bottom: 1; }
    #net-actions Button { width: 1fr; margin-right: 1; }
    #reels-container { width: 100%; height: 100%; border: solid $secondary; padding: 1; background: $surface; } #reels-actions { margin-bottom: 1; }
    /* Account View Styles */
    #account-container { width: 100%; height: 100%; border: solid $secondary; padding: 1; background: $surface; }
    #account-header { text-align: center; text-style: bold; width: 100%; color: $accent; margin-bottom: 1; }
    #account-card { height: auto; }
    .acc-title { text-style: bold; color: $success; }
    .acc-section { margin-top: 1; border-top: solid $secondary; padding-top: 1; height: auto;}
    .acc-section-title { text-style: bold; color: $warning; margin-bottom: 1; }
    #account-actions { margin-top: 1; border-top: solid $secondary; padding-top: 1; height: auto; }
    #account-actions Button { width: 1fr; margin: 0 1; }
    /* Extra View Styles */
    #extra-container { width: 100%; height: 100%; border: solid $secondary; padding: 1; background: $surface; }
    #extra-header { text-align: center; text-style: bold; width: 100%; color: $accent; margin-bottom: 1; }
    .action-row { height: auto; margin-bottom: 1; }
    .action-row Input { width: 3fr; }
    .action-row Button { width: 1fr; margin-left: 1; }
    #dl-thread-list { height: 10; margin-bottom: 1; border: round $primary; }
    #dl-log { height: 1fr; border: solid $accent; background: $background; padding: 1; }
    /* Notes View Styles */
    #notes-container { width: 100%; height: 100%; border: solid $secondary; padding: 1; background: $surface; }
    #notes-header { text-align: center; text-style: bold; width: 100%; color: $accent; margin-bottom: 1; }
    #music-container { border: thick $success; padding: 1; margin-bottom: 1; background: $background; }
    #music-header { text-style: bold; margin-bottom: 1; color: $success; }
    #notes-controls { margin-top: 1; margin-bottom: 1; }
    #notes-controls Button { width: 1fr; margin-right: 1;}
    /* Ghost Viewer Styles */
    #ghost-container { width: 100%; height: 100%; border: solid $secondary; padding: 1; background: $surface; }
    #ghost-header { text-align: center; text-style: bold; width: 100%; color: $success; margin-bottom: 1; }
    .ghost-tip { color: $warning; text-style: italic; margin-bottom: 1; }
    #ghost-panels { height: 1fr; margin-top: 1; }
    .ghost-panel { width: 1fr; height: 100%; border: solid $accent; margin: 0 1; padding: 0 1; }
    .panel-title { width: 100%; text-align: center; text-style: bold; margin-bottom: 1; color: $primary; }
    """

    def __init__(self):
        super().__init__()
        self.ig_client = Client()
        self.last_msg_id = None # Used for notifications

    def on_mount(self):
        """Standard startup sequence."""
        # Instead of a while True loop, we tell Textual to run this every 30 seconds
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
        """Silently checks for new DMs."""
        # Safety: Don't poll if not logged in
        if not getattr(self.ig_client, 'user_id', None):
            return 
            
        try:
            # Note: Fetching only 1 thread is fast
            threads = self.ig_client.direct_threads(amount=1)
            if threads and threads[0].messages:
                latest_msg = threads[0].messages[0]
                
                # If this is the first time polling, just save the ID
                if self.last_msg_id is None:
                    self.last_msg_id = latest_msg.id
                    return

                # If new message detected
                if latest_msg.id != self.last_msg_id:
                    self.last_msg_id = latest_msg.id
                    
                    # If someone ELSE sent it
                    if str(latest_msg.user_id) != str(self.ig_client.user_id):
                        sender = threads[0].thread_title or "Someone"
                        text = latest_msg.text if latest_msg.text else "📷 Media"
                        
                        # Show notification
                        self.app.call_from_thread(
                            self.notify, 
                            text, 
                            title=f"New message from {sender}",
                            severity="info"
                        )
        except Exception:
            pass

if __name__ == "__main__":
    try:
        app = InstaTermApp()
        app.run()
    except Exception as e:
        print(f"Application failed to start: {e}")
