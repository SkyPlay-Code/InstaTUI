# main.py
import os
import threading
import types
from textual.app import App
from textual import work
from instagrapi import Client
from instagrapi.utils.serialization import dumps

from login_screen import LoginScreen
from instagrapi.mixins.challenge import ChallengeChoice
from dashboard_screen import DashboardScreen
from challenge_screen import ChallengeScreen


def deep_find_key(data, target_key):
    """Recursively search for a key in nested dictionaries or lists."""
    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for key, value in data.items():
            result = deep_find_key(value, target_key)
            if result is not None:
                return result
    elif isinstance(data, list):
        for item in data:
            result = deep_find_key(item, target_key)
            if result is not None:
                return result
    return None


def patch_private_request(client):
    """Patches the instagrapi Client's low-level private_request method to intercept and resolve Bloks 'STEP_NAME' redirects."""
    original_private_request = client.private_request

    def custom_private_request(self, endpoint, data=None, *args, **kwargs):
        # Execute the original API request first
        response = original_private_request(endpoint, data, *args, **kwargs)
        
        # Intercept if the response contains the Bloks challenge step redirect
        if isinstance(response, dict) and response.get("step_name") == "STEP_NAME":
            bloks_action = response.get("bloks_action")
            challenge_context = response.get("challenge_context")
            
            if bloks_action == "com.bloks.www.ig.challenge.redirect.async" and challenge_context:
                bk_version = getattr(self, "bloks_versioning_id", None) or "5f56ef30aab00e509de4fcf740e00f147d3c906323bc327bc47999e096f20858"
                bk_context = {"bloks_version": bk_version, "styles_id": "instagram"}
                
                bloks_data = {
                    "bk_client_context": dumps(bk_context),
                    "challenge_context": challenge_context,
                }
                if bk_version:
                    bloks_data["bloks_versioning_id"] = bk_version

                try:
                    # Execute the asynchronous redirection request
                    # We call original_private_request directly to bypass this hook and avoid infinite recursion
                    bloks_response = original_private_request(f"bloks/apps/{bloks_action}/", bloks_data)
                    
                    # Extract resolved steps and authentication values
                    found_step = deep_find_key(bloks_response, "step_name")
                    found_context = deep_find_key(bloks_response, "challenge_context")
                    found_step_data = deep_find_key(bloks_response, "step_data")
                    
                    if found_step and found_step != "STEP_NAME":
                        new_response = {
                            "step_name": found_step,
                            "challenge_context": found_context or challenge_context,
                            "step_data": found_step_data or response.get("step_data", {}),
                            "status": "ok"
                        }
                        # Synchronize client state so calling functions retrieve the correct step name
                        self.last_json = new_response
                        return new_response
                    
                except Exception:
                    pass

        return response

    client.private_request = types.MethodType(custom_private_request, client)


class InstaTermApp(App):
    """The Main App Controller."""

    BINDINGS = [
        ("q", "quit", "Quit App")
    ]

    SCREENS = {
        "login": LoginScreen,
        "dashboard": DashboardScreen
    }

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
    #challenge-box {
        width: 50;
        height: auto;
        padding: 2;
        background: $surface;
        border: thick $error;
        align: center middle;
    }
    #challenge-title { text-align: center; text-style: bold; width: 100%; color: $error; margin-bottom: 1; }
    #challenge-desc { text-align: center; margin-bottom: 1; }
    #explore-container { width: 100%; height: 100%; border: solid $secondary; padding: 1; background: $surface; }
    #explore-header { text-align: center; text-style: bold; width: 100%; color: $accent; margin-bottom: 1; }
    .action-row Input { width: 2fr; }
    .action-row Button { width: 1fr; margin-left: 1; }
    """

    def __init__(self):
        super().__init__()
        self.ig_client = Client()
        self.last_msg_id = None
        
        # Lock to prevent overlapping notification polls
        self._polling_lock = threading.Lock()
        
        # --- THE CHALLENGE HANDLER PATCH & SETUP ---
        patch_private_request(self.ig_client)
        self.challenge_event = threading.Event()
        self.challenge_code = ""
        # We hook into instagrapi's built-in verification flow!
        self.ig_client.challenge_code_handler = self.gui_challenge_handler

    def gui_challenge_handler(self, username, choice):
        """Called automatically by instagrapi when Instagram locks the account!"""
        self.challenge_event.clear() # Reset the event
        
        # Notify the UI to render the popup
        self.call_from_thread(self.trigger_challenge_ui)
        
        # Block the API thread until the user presses "Submit" on the UI
        self.challenge_event.wait() 
        return self.challenge_code

    def trigger_challenge_ui(self):
        """Displays the popup and captures the user's keystrokes."""
        def callback(code):
            self.challenge_code = code
            self.challenge_event.set() # Unpauses the worker thread!
            self.notify("Code submitted. Waiting for Instagram's server...", severity="warning")

        # Push the screen and wait for the callback
        self.push_screen(ChallengeScreen(), callback)

    def on_mount(self):
        # Start the background polling interval
        self.set_interval(30, self.poll_notifications)
        
        if os.path.exists("session.json"):
            try:
                self.ig_client.load_settings("session.json")
                self.push_screen("dashboard")
            except Exception:
                self.push_screen("login")
        else:
            self.push_screen("login")

    def on_unmount(self):
        # Unblock any waiting threads to allow a clean exit
        self.challenge_event.set()

    @work(thread=True)
    def poll_notifications(self):
        if not getattr(self.ig_client, 'user_id', None):
            return 
        
        # Try to acquire the lock. If already acquired, skip this execution.
        if not self._polling_lock.acquire(blocking=False):
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
        finally:
            self._polling_lock.release()


if __name__ == "__main__":
    try:
        app = InstaTermApp()
        app.run()
    except Exception as e:
        print(f"Application failed to start: {e}")
