# main.py
import os
import subprocess
import threading

from textual import work
from textual.app import App

from challenge_screen import ChallengeScreen
from dashboard_screen import DashboardScreen
from instagrapi import Client
from login_screen import LoginScreen


class InstaTermApp(App):
    """The Main App Controller with Sidebar, Media Player, and Quality Toggling."""

    BINDINGS = [
        ("q", "quit", "Quit App"),
        ("t", "toggle_quality", "Toggle Quality (TCT/HD)")
    ]

    SCREENS = {
        "login": LoginScreen,
        "dashboard": DashboardScreen
    }

    # Fully merged and cleaned layout CSS
    CSS = """
    Screen { 
        align: center middle; 
        background: $background; 
    }
    
    TabPane { 
        padding: 1 2; 
        align: center middle; 
    }
    
    /* Left Sidebar Navigation Layout */
    #sidebar {
        width: 26;
        height: 100%;
        background: $surface;
        border-right: solid $secondary;
    }
    #sidebar-title {
        text-style: bold;
        text-align: center;
        width: 100%;
        color: $accent;
        padding: 1 0;
        border-bottom: solid $secondary;
    }
    #nav-list {
        background: transparent;
        height: 1fr;
    }
    #nav-list ListItem {
        padding-left: 1;
    }
    
    /* Right Content Area */
    #content-area {
        width: 1fr;
        height: 100%;
        padding: 1 2;
    }

    /* Login Form Styles */
    #login-form { 
        width: 45; 
        height: auto; 
        border: thick $primary; 
        padding: 2 4; 
        background: $surface; 
    }
    #title { 
        text-align: center; 
        width: 100%; 
        text-style: bold; 
        margin-bottom: 2; 
        color: $accent; 
    }
    Input { 
        margin-bottom: 1; 
    }
    Button { 
        width: 100%; 
        margin-top: 1; 
    }
    #status-msg { 
        text-align: center; 
        width: 100%; 
        color: yellow; 
        margin-top: 1; 
    }

    /* Containers Layout (Unified grouped rules) */
    #inbox-container, #notification-container, #notes-container, #profile-card, #network-container, #reels-container, #account-container, #explore-container, #extra-container {
        width: 100%;
        height: 100%;
        border: solid $secondary;
        padding: 1;
        background: $surface;
    }
    #inbox-container { 
        width: 90%; 
    }
    
    /* Unified Header Layouts */
    #inbox-header, #notification-header, #notif-header, #notes-header, #profile-username, #net-header, #reels-header, #account-header, #explore-header, #extra-header { 
        width: 100%; 
        text-align: center; 
        text-style: bold; 
        padding-bottom: 1; 
        border-bottom: solid $secondary; 
        margin-bottom: 1; 
        color: $accent; 
    }
    
    OptionList { 
        height: 1fr; 
        border: blank; 
    }
    #refresh-inbox-btn, #refresh-notes-btn { 
        margin-bottom: 1; 
    }

    /* Chat View Styles */
    #chat-main-container { 
        width: 80%; 
        height: 90%; 
        border: solid $secondary; 
        padding: 1; 
        background: $surface; 
    }
    #chat-header { 
        width: 100%; 
        text-align: center; 
        text-style: bold; 
        padding-bottom: 1; 
        border-bottom: solid $secondary; 
        color: $accent; 
    }
    #message-container { 
        height: 1fr; 
        border: round $primary; 
        padding: 1; 
        margin-top: 1; 
        margin-bottom: 1; 
        overflow-y: scroll; 
        background: $background; 
    }
    #input-container { 
        height: 3; 
    }
    #message-input { 
        width: 1fr; 
    }
    #send-btn { 
        width: 15; 
        margin-left: 1; 
    }
    #back-btn { 
        margin-top: 1; 
        width: 100%; 
    }
    .msg-me { 
        color: $success; 
        text-align: right; 
        width: auto; 
        max-width: 90%; 
        padding: 0 1; 
    }
    .msg-them { 
        color: $warning; 
        text-align: left; 
        width: auto; 
        max-width: 90%; 
        padding: 0 1; 
    }
    .msg-system { 
        color: $error; 
        text-align: center; 
        text-style: italic; 
        margin: 1 0; 
    }

    /* Profile View Styles */
    #profile-search { 
        margin-bottom: 1; 
    }
    #profile-top-section { 
        height: auto; 
        margin-bottom: 1; 
    }
    #profile-pic-container { 
        width: 50; 
        height: auto; 
        margin-right: 2; 
    }
    #profile-stats-container { 
        height: auto; 
        align-vertical: middle; 
    }
    #profile-counters { 
        color: $accent; 
    }
    #profile-bio { 
        margin-top: 1; 
        border-top: solid $secondary; 
        padding-top: 1; 
    }
    #profile-actions { 
        height: auto; 
        margin-top: 1; 
        border-top: solid $secondary; 
        padding-top: 1; 
    }
    #profile-actions Button { 
        width: 1fr; 
        margin: 0 1; 
    }

    /* Network Styles */
    #net-sub { 
        text-align: center; 
        width: 100%; 
        margin-bottom: 1; 
    }
    #scan-btn { 
        width: 100%; 
        margin-bottom: 1; 
    }
    
    /* Notes & Extra Styles */
    #music-container { 
        border: thick $success; 
        padding: 1; 
        margin-bottom: 1; 
        background: $background; 
    }
    #music-header { 
        text-style: bold; 
        margin-bottom: 1; 
        color: $success; 
    }
    #notes-controls { 
        margin-top: 1; 
        margin-bottom: 1; 
    }
    #notes-controls Button { 
        width: 1fr; 
        margin-right: 1;
    }
    .action-row { 
        height: auto; 
        margin-bottom: 1; 
    }
    .action-row Input { 
        width: 2fr; 
    }
    .action-row Button { 
        width: 1fr; 
        margin-left: 1; 
    }
    #dl-thread-list { 
        height: 10; 
        margin-bottom: 1; 
        border: round $primary; 
    }
    #dl-log { 
        height: 1fr; 
        border: solid $accent; 
        background: $background; 
        padding: 1; 
    }

    /* Challenge Box Popup */
    #challenge-box { 
        width: 50; 
        height: auto; 
        padding: 2; 
        background: $surface; 
        border: thick $error; 
        align: center middle; 
    }
    #challenge-title { 
        text-align: center; 
        text-style: bold; 
        width: 100%; 
        color: $error; 
        margin-bottom: 1; 
    }
    #challenge-desc { 
        text-align: center; 
        margin-bottom: 1; 
    }
    
    /* Notifications & Settings Styles */
    #notif-controls { 
        margin-top: 1; 
        margin-bottom: 1; 
    }
    #notif-controls Button { 
        width: 1fr; 
        margin-right: 1;
    }
    #notif-settings-panel { 
        border: thick $warning; 
        padding: 1; 
        margin-bottom: 1; 
        background: $background; 
        height: auto;
    }
    #settings-title { 
        text-style: bold; 
        margin-bottom: 1; 
        color: $warning; 
    }
    #settings-options-list { 
        height: 10; 
        margin-bottom: 1; 
    }
    """

    def __init__(self):
        super().__init__()
        self.ig_client = Client()
        self.last_msg_id = None
        
        # Lock to prevent race conditions during concurrent API and polling requests
        self.api_lock = threading.Lock()
        
        # Quality Selector ("lowq" or "hd")
        self.media_quality = "lowq"
        
        self.challenge_event = threading.Event()
        self.challenge_code = ""
        self.ig_client.challenge_code_handler = self.gui_challenge_handler

    def action_toggle_quality(self) -> None:
        """The keybinding handler. Changes quality instantly with 't'!"""
        if self.media_quality == "lowq":
            self.media_quality = "hd"
            self.notify("📺 Media Quality: HIGH-DEFINITION (Sixel/Kitty Mode)", severity="information")
        else:
            self.media_quality = "lowq"
            self.notify("📟 Media Quality: RETRO TCT (Terminal Blocks)", severity="warning")

    # ==========================================
    # 👑 RESTORED: THE UNIFIED MEDIA PLAYER PIPELINE
    # ==========================================
    def play_media_file(self, path: str, is_video: bool = True) -> None:
        """Plays media using the strict quality priority chain inside the terminal."""
        is_hd = self.media_quality == "hd"
        vo_drivers = "kitty,sixel,gpu,tct" if is_hd else "tct"

        # Safely structured array command prevents path spacing issues & shell injection
        cmd = ["mpv", f"--vo={vo_drivers}", "--quiet", path]
        if not is_video:
            cmd.append("--image-display-duration=inf")

        with self.suspend():
            print("\033[2J\033[H", end="") 
            print(f"🚀 IN-APP MEDIA PLAYER (Quality Mode: {self.media_quality.upper()})")
            print("Press 'q' to close media and return to the TUI.")
            print("-" * 50)
            try:
                subprocess.run(cmd)
            except FileNotFoundError:
                print("\n❌ Error: 'mpv' media player is not installed or not in PATH.")
                print("Please install mpv to enable media rendering.")
                input("\nPress Enter to return to the app...")
            
        self.refresh() # Always unfreeze the terminal cleanly!

    def gui_challenge_handler(self, username: str, choice=None) -> str:  # pyright: ignore[reportUnusedParameter]
        """Signals background operations to wait while showing the challenge modal."""
        self.challenge_event.clear()
        self.call_from_thread(self.trigger_challenge_ui)
        self.challenge_event.wait() 
        return self.challenge_code

    def trigger_challenge_ui(self):
        """Pushes challenge screen modal to prompt user for codes."""
        def callback(code):
            self.challenge_code = code if code is not None else ""
            self.challenge_event.set()
            self.notify("Code submitted. Waiting for Instagram...", severity="warning")
        self.push_screen(ChallengeScreen(), callback)

    def on_mount(self):
        self.set_interval(30, self.poll_notifications)
        self.load_initial_session()

    @work(thread=True, exclusive=True)
    def load_initial_session(self):
        """Asynchronously loads the initial session file to prevent startup deadlocks."""
        if os.path.exists("session.json"):
            try:
                with self.api_lock:
                    self.ig_client.load_settings("session.json")
                self.call_from_thread(self.push_screen, "dashboard")
            except Exception:
                self.call_from_thread(self.push_screen, "login")
        else:
            self.call_from_thread(self.push_screen, "login")

    @work(thread=True, exclusive=True)
    def poll_notifications(self):
        """Polls direct message updates concurrently and thread-safely."""
        if not getattr(self.ig_client, 'user_id', None):
            return 
        try:
            with self.api_lock:
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
                        # FIXED: 'info' severity changed to 'information' to comply with Textual specifications
                        self.call_from_thread(self.notify, text, title=f"New message from {sender}", severity="information")
        except Exception:
            pass

    def on_unmount(self) -> None:
        """Forces verification events to set, freeing lingering threads during app exit."""
        self.challenge_event.set()


if __name__ == "__main__":
    try:
        app = InstaTermApp()
        app.run()
    except Exception as e:
        print(f"Application failed to start: {e}")