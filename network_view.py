# network_view.py
from textual.widgets import OptionList, LoadingIndicator, Label, Button, Input, TabbedContent
from textual.containers import Vertical, Horizontal
from textual import work
import time

class NetworkView(Vertical):
    """Scans and analyzes followers/following lists."""

    def compose(self):
        with Vertical(id="network-container"):
            yield Label("🕸️ Network Explorer", id="net-header")
            yield Input(placeholder="🔍 Target username (Leave blank for YOUR account)...", id="net-target")
            
            with Horizontal(id="net-actions"):
                yield Button("👥 Followers", id="btn-followers", variant="primary")
                yield Button("👤 Following", id="btn-following", variant="primary")
                yield Button("🤝 Mutuals", id="btn-mutuals", variant="success")
                yield Button("🚫 Non-Followers", id="btn-traitors", variant="error")
                
            yield LoadingIndicator(id="net-loading")
            yield OptionList(id="net-list")

    def on_mount(self):
        self.query_one("#net-loading").display = False
        self.query_one("#net-list").display = False
        self.current_user_cache = [] 

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "net-target":
            self.app.notify("Select a scan mode below!", severity="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ["btn-followers", "btn-following", "btn-mutuals", "btn-traitors"]:
            self.query_one("#net-loading").display = True
            self.query_one("#net-list").display = False
            
            for btn in self.query(Button):
                btn.disabled = True
                
            target_username = self.query_one("#net-target", Input).value.strip()
            self.run_scanner(event.button.id, target_username)

    @work(thread=True)
    def run_scanner(self, mode, username):
        cl = self.app.ig_client
        try:
            # 1. Decide on Target and Safety Limits
            if not username:
                target_id = cl.user_id
                display_name = "You"
                # Safe to fetch a lot for YOURSELF
                fetch_amount = 200 
            else:
                self.app.call_from_thread(self.update_status, f"🔍 Finding ID for @{username}...")
                target_id = cl.user_id_from_username(username)
                display_name = f"@{username}"
                # ⚠️ DANGER ZONE: Limit to 40 to avoid bans when scanning OTHERS
                fetch_amount = 40 
                self.app.call_from_thread(self.app.notify, f"Applying Safety Limit: 40 users max for third-party scans.", severity="warning")

            self.app.call_from_thread(self.update_status, "📡 Downloading Lists (Actively avoiding bans...)")
            
            # Artificial delay so Instagram doesn't think we are a robot
            time.sleep(2) 

            final_list = []
            
            if mode == "btn-followers":
                data = cl.user_followers(target_id, amount=fetch_amount)
                final_list = list(data.values())
                
            elif mode == "btn-following":
                data = cl.user_following(target_id, amount=fetch_amount)
                final_list = list(data.values())
                
            elif mode in ["btn-mutuals", "btn-traitors"]:
                self.app.call_from_thread(self.update_status, "📡 Downloading Followers AND Following...")
                following = cl.user_following(target_id, amount=fetch_amount)
                time.sleep(2) # Safety Pause
                followers = cl.user_followers(target_id, amount=fetch_amount)
                
                self.app.call_from_thread(self.update_status, "⚙️ Crunching data...")
                for uid, user_obj in following.items():
                    if mode == "btn-traitors" and uid not in followers:
                        final_list.append(user_obj)
                    elif mode == "btn-mutuals" and uid in followers:
                        final_list.append(user_obj)

            self.app.call_from_thread(self.display_results, final_list, mode, display_name)

        except Exception as e:
            err_msg = str(e)
            if "private" in err_msg.lower() or "not authorized" in err_msg.lower():
                self.app.call_from_thread(self.app.notify, f"❌ Cannot scan: Profile is private!", severity="error")
            elif "challenge" in err_msg.lower():
                self.app.call_from_thread(self.app.notify, "⚠️ BOT DETECTED: Log into real IG app to clear the checkpoint!", severity="error")
            else:
                self.app.call_from_thread(self.app.notify, f"API Error: {err_msg[:40]}", severity="error")
            self.app.call_from_thread(self.reset_ui)

    def update_status(self, text):
        self.query_one("#net-header").update(f"🕸️ {text}")

    def reset_ui(self):
        for btn in self.query(Button):
            btn.disabled = False
        self.query_one("#net-loading").display = False

    def display_results(self, user_list, mode, display_name):
        self.reset_ui()
        self.current_user_cache = user_list
        
        mode_titles = {
            "btn-followers": f"👥 Followers of {display_name}",
            "btn-following": f"👤 Following list of {display_name}",
            "btn-mutuals": f"🤝 Friends of {display_name}",
            "btn-traitors": f"🚫 Non-Followers of {display_name}"
        }
        self.update_status(mode_titles.get(mode))
        
        list_ui = self.query_one("#net-list", OptionList)
        list_ui.clear_options()
        list_ui.display = True
        
        if not user_list:
            list_ui.add_option("No users found.")
            return

        for u in user_list:
            list_ui.add_option(f"👤 @{u.username} - ({u.full_name})")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if not self.current_user_cache or event.option_index >= len(self.current_user_cache): return
        
        selected_user = self.current_user_cache[event.option_index]
        username = selected_user.username
        
        try:
            self.screen.query_one(TabbedContent).active = "profile-tab"
            from profile_view import ProfileView
            profile_viewer = self.screen.query_one(ProfileView)
            
            profile_viewer.query_one("#profile-search", Input).value = username
            profile_viewer.query_one("#profile-card").display = False
            profile_viewer.query_one("#profile-loading").display = True
            profile_viewer.fetch_profile(username)
        except Exception as e:
            self.app.notify(f"Navigation error: {e}", severity="error")
