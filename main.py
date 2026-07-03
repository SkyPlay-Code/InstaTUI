# main.py
import os
import subprocess
import threading

from textual import work, events
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

    CSS = """
    Screen { background: $background; }
    
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
        padding-top: 1;
        height: 3;
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
    LoginScreen {
        align: center middle;
    }
    #login-form { width: 45; height: auto; border: thick $primary; padding: 2 4; background: $surface; margin: 4 0; }
    #title { text-align: center; width: 100%; text-style: bold; margin-bottom: 2; color: $accent; }
    Input { margin-bottom: 1; }
    Button { width: 100%; margin-top: 1; }
    #status-msg { text-align: center; width: 100%; color: yellow; margin-top: 1; }

    /* Inbox Styles */
    #inbox-container { width: 100%; height: 100%; border: solid $secondary; padding: 1; background: $surface; }
    #inbox-header { width: 100%; text-align: center; text-style: bold; padding-bottom: 1; border-bottom: solid $secondary; margin-bottom: 1; color: $accent; }
    OptionList { height: 1fr; border: blank; }
    #refresh-inbox-btn { margin-bottom: 1; }

    /* 👑 CHAT VIEW: JUICED FOR MAXIMUM TERMINAL SPACE 👑 */
    #chat-main-container { 
        width: 100%; 
        height: 100%; 
        border: solid $secondary; 
        padding: 1; 
        background: $surface; 
    }
    #chat-header { 
        width: 100%; 
        height: 3;
        text-align: center; 
        text-style: bold; 
        padding-top: 1;
        border-bottom: solid $secondary; 
        color: $accent; 
    }
    #message-container { 
        height: 1fr; /* Takes up 100% of the remaining vertical space! */
        border: round $primary; 
        padding: 1 2; 
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
        height: 3;
    }
    #send-btn { 
        width: 16; 
        height: 3;
        margin-left: 1; 
    }
    #chat-footer {
        height: 3;
        margin-top: 1;
    }
    #chat-footer Button {
        width: 1fr; /* Puts Back and Refresh flat side-by-side in a 50/50 split! */
        margin: 0 1;
        height: 3;
    }

    /* Chat Message & Naming Colors */
    .msg-me { 
        color: $success; 
        text-align: right; 
        width: auto; 
        max-width: 90%; 
        padding: 0 1; 
    }
    .msg-me Label, .msg-me Static, .msg-me .msg-name { 
        color: $success; 
    }
    .msg-them { 
        color: $warning; 
        text-align: left; 
        width: auto; 
        max-width: 90%; 
        padding: 0 1; 
    }
    .msg-them Label, .msg-them Static, .msg-them .msg-name { 
        color: $warning; 
    }
    .msg-system { 
        color: $error; 
        text-align: center; 
        text-style: italic; 
        margin: 1 0; 
    }

    /* Profile View Styles */
    #profile-search { margin-bottom: 1; }
    #profile-top-section { height: auto; margin-bottom: 1; }
    #profile-pic-container { width: 36; height: auto; margin-right: 2; }
    #profile-stats-container { height: auto; align-vertical: middle; }
    #profile-counters { color: $accent; }
    #profile-bio { margin-top: 1; border-top: solid $secondary; padding-top: 1; }
    #profile-actions { height: auto; margin-top: 1; border-top: solid $secondary; padding-top: 1; }
    #profile-actions Button { width: 1fr; margin: 0 1; }

    /* Network & Notifications Styles */
    #net-sub { text-align: center; width: 100%; margin-bottom: 1; }
    #scan-btn { width: 100%; margin-bottom: 1; }
    #notif-controls { margin-top: 1; margin-bottom: 1; }
    #notif-controls Button { width: 1fr; margin-right: 1; }
    
    /* Notes & Extra Styles */
    #music-container { border: thick $success; padding: 1; margin-bottom: 1; background: $background; }
    #music-header { text-style: bold; margin-bottom: 1; color: $success; }
    #notes-controls { margin-top: 1; margin-bottom: 1; }
    #notes-controls Button { width: 1fr; margin-right: 1;}
    .action-row { height: auto; margin-bottom: 1; }
    .action-row Input { width: 2fr; }
    .action-row Button { width: 1fr; margin-left: 1; }
    #dl-thread-list { height: 10; margin-bottom: 1; border: round $primary; }
    #dl-log { height: 1fr; border: solid $accent; background: $background; padding: 1; }

    /* Challenge Box Popup */
    #challenge-box { width: 50; height: auto; padding: 2; background: $surface; border: thick $error; align: center middle; }
    #challenge-title { text-align: center; text-style: bold; width: 100%; color: $error; margin-bottom: 1; }
    #challenge-desc { text-align: center; margin-bottom: 1; }
     
    #account-edit-form { height: auto; }
    #account-edit-form Label { margin-top: 1; text-style: bold; color: $accent; }
    #edit-actions { margin-top: 1; border-top: solid $secondary; padding-top: 1; height: auto; }
    #edit-actions Button { width: 1fr; margin: 0 1; }    

    /* ------------- Message Row Action Styling ------------- */
    .msg-row {
        height: auto;
        margin-bottom: 1;
        align-vertical: middle;
    }
    .msg-row Label {
        width: 1fr; /* Text bubble takes up 100% of the row */
        height: auto;
    }
    
    /* Discrete small buttons next to each text bubble */
    .msg-action-btn {
        min-width: 4;
        width: 4;
        height: 1;
        border: none;
        padding: 0;
        margin-left: 1;
        background: transparent;
        color: $text-muted;
    }
    .msg-action-btn:hover {
        color: $accent;
        background: $surface;
    }

    /* Reaction Popup Box */
    #reaction-box {
        width: 40;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
        align: center middle;
    }
    #reaction-title { text-align: center; text-style: bold; color: $accent; margin-bottom: 1; }
    #reaction-actions { height: auto; margin-top: 1; }
    #reaction-actions Button { width: 1fr; margin: 0 1; }
    """

    def __init__(self):
        super().__init__()
        self.ig_client = Client()
        self.last_msg_id = None
        self.api_lock = threading.Lock()
        self.media_quality = "lowq"
        self.challenge_event = threading.Event()
        self.challenge_code = ""
        self.ig_client.challenge_code_handler = self.gui_challenge_handler

    def action_toggle_quality(self) -> None:
        if self.media_quality == "lowq":
            self.media_quality = "hd"
            self.notify("📺 Media Quality: HIGH-DEFINITION (Sixel/Kitty Mode)", severity="information")
        else:
            self.media_quality = "lowq"
            self.notify("📟 Media Quality: RETRO TCT (Terminal Blocks)", severity="warning")

    # ==========================================
    # 👑 RESILIENT MEDIA PLAYER PIPELINE
    # ==========================================
    def play_media_file(self, path: str, is_video: bool = True, cleanup: bool = False) -> None:
        """Plays media. Opens a high-definition graphical GUI window for images or terminal view for video."""
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            with self.suspend():
                print(f"\n❌ Error: The downloaded image file at '{path}' is empty or missing.")
                input("\nPress Enter to return to the app...")
            return

        is_hd = self.media_quality == "hd"

        # If it's an image, let mpv open as an external graphical GUI window
        if not is_video:
            cmd = ["mpv", "--quiet", path, "--image-display-duration=inf"]
        else:
            vo_drivers = "kitty,sixel,gpu,tct" if is_hd else "tct"
            cmd = ["mpv", f"--vo={vo_drivers}", "--quiet", path]

        with self.suspend():
            print("\033[2J\033[H", end="") 
            print(f"🚀 IN-APP MEDIA PLAYER (Quality Mode: {self.media_quality.upper()})")
            print("Press 'q' to close media and return to the TUI.")
            print("-" * 50)
            
            played_successfully = False
            try:
                result = subprocess.run(cmd)
                if result.returncode == 0:
                    played_successfully = True
                else:
                    fallback_cmd = ["mpv", "--quiet", path]
                    if not is_video:
                        fallback_cmd.append("--image-display-duration=inf")
                    result = subprocess.run(fallback_cmd)
                    if result.returncode == 0:
                        played_successfully = True
            except FileNotFoundError:
                pass

            if not played_successfully:
                print("\n⚠️ 'mpv' failed or is not installed.")
                print("Launching your system's default native graphical image viewer instead...")
                try:
                    import platform
                    current_os = platform.system()
                    if current_os == "Darwin":  # macOS
                        subprocess.run(["open", path])
                        played_successfully = True
                    elif current_os == "Windows":  # Windows
                        os.startfile(path)
                        played_successfully = True
                    else:  # Linux/Unix
                        subprocess.run(["xdg-open", path])
                        played_successfully = True
                except Exception as e:
                    print(f"\n❌ OS Native view launcher failed: {e}")
                    input("\nPress Enter to return to the app...")

        self.refresh()

        if cleanup and os.path.exists(path):
            if played_successfully and not is_video:
                def delayed_cleanup():
                    import time
                    time.sleep(10)
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except Exception:
                        pass
                threading.Thread(target=delayed_cleanup, daemon=True).start()
            else:
                try:
                    os.remove(path)
                except Exception:
                    pass

    # ==========================================
    # 🎯 ROOT-LEVEL GLOBAL KEY INTERCEPTOR
    # ==========================================
    def on_key(self, event: events.Key) -> None:
        """Globally intercepts the 'q' key to perform back navigation or quit when at the root menu."""
        if event.key == "q":
            # If typing inside a search bar or text input, let "q" render normally
            if self.focused and self.focused.__class__.__name__ == "Input":
                return

            active_screen = self.screen
            screen_name = active_screen.__class__.__name__

            if screen_name == "DashboardScreen":
                # Check if the sidebar navigation menu is already focused
                nav_list_already_focused = False
                try:
                    nav_list = active_screen.query_one("#nav-list")
                    if nav_list.has_focus:
                        nav_list_already_focused = True
                except Exception:
                    pass

                # Check if the profile search card is currently visible on screen
                profile_card_visible = False
                try:
                    profile_view = active_screen.query_one("ProfileView")
                    if profile_view.query_one("#profile-card").display:
                        profile_card_visible = True
                except Exception:
                    pass

                # If the sidebar list is already focused AND no search card is displayed,
                # then pressing 'q' means exiting the main interface/app completely.
                if nav_list_already_focused and not profile_card_visible:
                    self.exit()
                    return

                # Otherwise, intercept the keypress to navigate "Back"
                event.prevent_default()
                event.stop()

                # 1. Reset the ProfileView search card if displayed
                if profile_card_visible:
                    try:
                        profile_view = active_screen.query_one("ProfileView")
                        profile_view.query_one("#profile-card").display = False
                        search_input = profile_view.query_one("#profile-search")
                        search_input.value = ""
                        search_input.focus()
                        return
                    except Exception:
                        pass

                # 2. Revert the active view back to the main interface/first tab
                switched = False
                try:
                    from textual.widgets import ContentSwitcher
                    switcher = active_screen.query_one(ContentSwitcher)
                    if switcher.children:
                        switcher.current = switcher.children[0].id
                        switched = True
                except Exception:
                    pass

                if not switched:
                    try:
                        containers = [
                            "#inbox-container", "#notification-container", "#notes-container",
                            "#profile-card", "#network-container", "#reels-container",
                            "#account-container", "#explore-container", "#extra-container"
                        ]
                        for container_id in containers:
                            try:
                                container = active_screen.query_one(container_id)
                                if container_id == "#inbox-container":
                                    container.display = True
                                else:
                                    container.display = False
                            except Exception:
                                pass
                    except Exception:
                        pass

                # 3. Focus the navigation list in the sidebar and highlight the first item
                try:
                    nav_list = active_screen.query_one("#nav-list")
                    if hasattr(nav_list, "highlighted"):
                        nav_list.highlighted = 0
                    elif hasattr(nav_list, "index"):
                        nav_list.index = 0
                    nav_list.focus()
                    self.notify("Returned to main menu", severity="information")
                except Exception:
                    pass
                return

            # If we are on a modal or verification pop-up, pop the screen stack
            elif len(self.screen_stack) > 1:
                event.prevent_default()
                event.stop()
                self.pop_screen()
                return

    def gui_challenge_handler(self, username: str, choice=None) -> str:  # pyright: ignore[reportUnusedParameter]
        self.challenge_event.clear()
        self.call_from_thread(self.trigger_challenge_ui)
        self.challenge_event.wait() 
        return self.challenge_code

    def trigger_challenge_ui(self):
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
                        self.call_from_thread(self.notify, text, title=f"New message from {sender}", severity="information")
        except Exception:
            pass

    def on_unmount(self) -> None:
        self.challenge_event.set()


if __name__ == "__main__":
    try:
        app = InstaTermApp()
        app.run()
    except Exception as e:
        print(f"Application failed to start: {e}")