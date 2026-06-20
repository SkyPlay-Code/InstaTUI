# notification_view.py
import datetime
from textual.widgets import OptionList, Label, Button, Input, ContentSwitcher
from textual.containers import Vertical, Horizontal
from textual import work

class NotificationView(Vertical):
    """View live activity feed and manage push notification settings."""

    def compose(self):
        with Vertical(id="notification-container"):
            yield Label("🔔 My Recent Activity", id="notif-header", classes="section-header")
            
            # ContentSwitcher acts as a clean panel navigator
            with ContentSwitcher(initial="feed-panel", id="notif-switcher"):
                
                # --- PANEL 1: FEED VIEW ---
                with Vertical(id="feed-panel"):
                    with Horizontal(id="notif-controls", classes="action-row"):
                        yield Button("🔄 Refresh Feed", id="btn-notif-refresh", variant="primary")
                        yield Button("⚙️ Manage Alerts", id="btn-notif-settings", variant="warning")
                    yield OptionList(id="notif-list")

                # --- PANEL 2: SETTINGS PANEL ---
                with Vertical(id="notif-settings-panel"):
                    yield Label("⚙️ Change Push Notification Rules", id="settings-title")
                    yield OptionList(
                        "🔇 Mute All: 1 Hour",
                        "🔇 Mute All: 8 Hours",
                        "🔕 Disable All Notifications",
                        "❤️ Likes: Turn ON (Everyone)",
                        "❤️ Likes: Turn OFF",
                        "💬 Comments: Turn ON (Everyone)",
                        "💬 Comments: Turn OFF",
                        id="settings-options-list"
                    )
                    with Horizontal(classes="action-row"):
                        yield Button("Apply Rule", id="btn-apply-setting", variant="success")
                        yield Button("Close Settings", id="btn-close-settings", variant="error")

    def on_mount(self):
        self.stories_cache = []  # Caches the raw notifications
        self.fetch_notifications()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        switcher = self.query_one("#notif-switcher", ContentSwitcher)

        if event.button.id == "btn-notif-refresh":
            self.fetch_notifications()
            
        elif event.button.id == "btn-notif-settings":
            switcher.current = "notif-settings-panel"
            
        elif event.button.id == "btn-close-settings":
            switcher.current = "feed-panel"
            
        elif event.button.id == "btn-apply-setting":
            opt_list = self.query_one("#settings-options-list", OptionList)
            if opt_list.highlighted is not None:
                self.apply_push_rule(opt_list.highlighted)

    # ==========================
    # WORKER THREADS (API CALLS)
    # ==========================

    @work(thread=True)
    def fetch_notifications(self):
        cl = self.app.ig_client
        # Toggle loading state on the main thread safely
        self.call_from_thread(self.set_ui_loading, True)
        try:
            # Native news_inbox_v1 API
            response = cl.news_inbox_v1(mark_as_seen=True)
            
            new_stories = response.get("new_stories", [])
            old_stories = response.get("old_stories", [])
            all_stories = new_stories + old_stories
            
            self.call_from_thread(self.display_notifications, all_stories)
        except Exception as e:
            self.call_from_thread(self.app.notify, f"Feed Error: {e}", severity="error")
            self.call_from_thread(self.set_ui_loading, False)

    @work(thread=True)
    def apply_push_rule(self, index):
        cl = self.app.ig_client
        try:
            self.call_from_thread(self.app.notify, "Sending push rule to Instagram...")
            
            if index == 0:
                cl.notification_mute_all("1_hour")
            elif index == 1:
                cl.notification_mute_all("8_hour")
            elif index == 2:
                cl.notification_disable()
            elif index == 3:
                cl.notification_likes("everyone")
            elif index == 4:
                cl.notification_likes("off")
            elif index == 5:
                cl.notification_comments("everyone")
            elif index == 6:
                cl.notification_comments("off")
                
            self.call_from_thread(self.app.notify, "✅ Push Settings Updated!")
            # Triggers helper method on the main thread to avoid unsafe evaluation
            self.call_from_thread(self.close_settings_ui)
        except Exception as e:
            self.call_from_thread(self.app.notify, f"Settings Error: {e}", severity="error")

    # ==========================
    # UI ACTIONS (MAIN THREAD ONLY)
    # ==========================

    def set_ui_loading(self, loading: bool) -> None:
        """Toggle native loader on the list element."""
        self.query_one("#notif-list", OptionList).loading = loading

    def close_settings_ui(self) -> None:
        """Helper to simulate button press to close settings on main thread."""
        self.query_one("#btn-close-settings", Button).press()

    def display_notifications(self, stories):
        self.stories_cache = stories
        self.set_ui_loading(False)
        
        list_ui = self.query_one("#notif-list", OptionList)
        list_ui.clear_options()
        
        if not stories:
            list_ui.add_option("No recent activity found.")
            return

        for story in stories:
            args = story.get("args", {})
            text = args.get("text", "")
            
            # Safe float-timestamp conversion
            ts = args.get("timestamp")
            time_str = ""
            if ts:
                try:
                    time_str = f" [{datetime.datetime.fromtimestamp(float(ts)).strftime('%m/%d %I:%M %p')}]"
                except (ValueError, TypeError):
                    pass
                
            list_ui.add_option(f"🔔 {text}{time_str}")
            
        self.query_one("#notif-header").update(f"🔔 Recent Activity ({len(stories)} entries)")

    def extract_username(self, story_dict):
        """Finds the username of who liked/commented from the metadata."""
        args = story_dict.get("args", {})
        links = args.get("links", [])
        for link in links:
            if link.get("type") == "user":
                start = link.get("start", 0)
                end = link.get("end", 0)
                text = args.get("text", "")
                username = text[start:end].strip("@").strip()
                return username if username else None
        return None

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Click-to-Profile Navigation."""
        # Fix: Prevent IndexError when clicking list items if cache is empty
        if not self.stories_cache or event.option_index >= len(self.stories_cache):
            return
        
        selected_story = self.stories_cache[event.option_index]
        username = self.extract_username(selected_story)
        
        if username:
            self.app.notify(f"Jumping to @{username}'s Profile...")
            
            # Switch tabs to profile
            from textual.widgets import TabbedContent
            self.screen.query_one(TabbedContent).active = "profile-tab"
            
            from profile_view import ProfileView
            pv = self.screen.query_one(ProfileView)
            
            # Input now imported correctly at file head level
            pv.query_one("#profile-search", Input).value = username
            pv.query_one("#profile-card").display = False
            pv.query_one("#profile-loading").display = True
            pv.fetch_profile(username)
        else:
            self.app.notify("Could not link this notification to a profile.", severity="warning")