# explore_view.py
import os
import subprocess
from textual.widgets import OptionList, LoadingIndicator, Label, Button, Input, TabbedContent
from textual.containers import Vertical, Horizontal
from textual import work

class ExploreView(Vertical):
    """Global Discovery Engine for Hashtags and User Searches."""

    def compose(self):
        with Vertical(id="explore-container"):
            yield Label("🌍 Global Discovery Engine", id="explore-header", classes="section-header")
            
            with Horizontal(classes="action-row"):
                yield Input(placeholder="Type a #hashtag or keyword...", id="explore-input")
                yield Button("🔥 Top Posts", id="btn-top", variant="primary")
                yield Button("🆕 Recent", id="btn-recent", variant="success")
                yield Button("👥 Find Users", id="btn-users", variant="warning")
                
            yield LoadingIndicator(id="explore-loading")
            yield OptionList(id="explore-list")

    def on_mount(self):
        self.query_one("#explore-loading").display = False
        self.explore_cache = []
        self.current_mode = None

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "explore-input":
            self.app.notify("Select a search mode (Top Posts / Recent / Users) below!", severity="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        query = self.query_one("#explore-input").value.strip()
        if not query:
            self.app.notify("Enter a search term first!", severity="error")
            return
            
        self.query_one("#explore-loading").display = True
        self.query_one("#explore-list").display = False
        for btn in self.query(Button): btn.disabled = True
        
        if event.button.id in ["btn-top", "btn-recent"]:
            self.current_mode = "media"
            # Remove hashtag if they accidentally typed it, the API doesn't want it!
            clean_tag = query.replace("#", "")
            self.fetch_hashtag_media(clean_tag, event.button.id)
            
        elif event.button.id == "btn-users":
            self.current_mode = "users"
            self.search_global_users(query)

    @work(thread=True)
    def fetch_hashtag_media(self, tag, mode):
        cl = self.app.ig_client
        try:
            self.app.call_from_thread(self.update_status, f"Scraping global database for #{tag}...")
            
            # Using your hashtag.py blueprints natively!
            if mode == "btn-top":
                medias = cl.hashtag_medias_top_v1(tag, amount=20)
            else:
                medias = cl.hashtag_medias_recent_v1(tag, amount=20)
            
            self.app.call_from_thread(self.display_results, medias, f"#{tag} ({mode.replace('btn-', '')})")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Explore Error: {e}", severity="error")
            self.app.call_from_thread(self.reset_ui)

    @work(thread=True)
    def search_global_users(self, query):
        cl = self.app.ig_client
        try:
            self.app.call_from_thread(self.update_status, f"Searching global accounts for '{query}'...")
            # Using the fbsearch.py native wrapper!
            users = cl.search_users(query)
            self.app.call_from_thread(self.display_results, users, f"Users matching '{query}'")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Search Error: {e}", severity="error")
            self.app.call_from_thread(self.reset_ui)

    def update_status(self, text):
        self.query_one("#explore-header").update(f"🌍 {text}")

    def reset_ui(self):
        for btn in self.query(Button): btn.disabled = False
        self.query_one("#explore-loading").display = False

    def display_results(self, items, title):
        self.reset_ui()
        self.explore_cache = items
        self.update_status(f"Found {len(items)} results for: {title}")
        
        list_ui = self.query_one("#explore-list", OptionList)
        list_ui.clear_options()
        list_ui.display = True
        
        if not items:
            list_ui.add_option("No results found.")
            return

        for item in items:
            if self.current_mode == "media":
                author = getattr(item.user, 'username', 'unknown') if getattr(item, 'user', None) else 'unknown'
                likes = getattr(item, 'like_count', 0)
                cap = getattr(item, 'caption_text', '') or ""
                is_vid = getattr(item, 'media_type', 1) == 2
                icon = "🎥 Video" if is_vid else "📸 Photo"
                list_ui.add_option(f"{icon} @{author} | ❤️ {likes} | {cap.replace(chr(10), ' ')[:50]}...")
                
            elif self.current_mode == "users":
                list_ui.add_option(f"👤 @{item.username} - {item.full_name}")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if not self.explore_cache: return
        item = self.explore_cache[event.option_index]
        
        if self.current_mode == "users":
            self.app.notify(f"Jumping to Profile: @{item.username}")
            
            # Switch to Profile Tab
            self.screen.query_one(TabbedContent).active = "profile-tab"
            from profile_view import ProfileView
            pv = self.screen.query_one(ProfileView)
            
            pv.query_one("#profile-search", Input).value = item.username
            pv.query_one("#profile-card").display = False
            pv.query_one("#profile-loading").display = True
            pv.fetch_profile(item.username)
            
        elif self.current_mode == "media":
            self.app.notify("Securely downloading HD Media...", timeout=3)
            self.play_media(item)

    @work(thread=True)
    def play_media(self, media):
        cl = self.app.ig_client
        path = None
        is_vid = getattr(media, 'media_type', 1) == 2
        try:
            # We use the built-in native downloaders so we NEVER get 404 CDN blocks!
            if is_vid:
                downloaded_path = cl.video_download(media.pk, folder=".")
            else:
                downloaded_path = cl.photo_download(media.pk, folder=".")
                
            if downloaded_path:
                path = str(downloaded_path)
            else:
                self.app.call_from_thread(self.app.notify, "Download failed: No path returned", severity="error")
                return
                
            with self.app.suspend():
                print("\033[2J\033[H", end="") 
                print(f"🌍 GLOBAL DISCOVERY VIEWER (Press 'q' to return to TUI)")
                print("-" * 50)
                
                # Using list arguments with shell=False (default) avoids shell injection entirely
                cmd = ["mpv", "--vo=tct", "--quiet"]
                if not is_vid:
                    cmd.append("--image-display-duration=inf")
                cmd.append(path)
                
                try:
                    subprocess.run(cmd)
                except FileNotFoundError:
                    self.app.call_from_thread(
                        self.app.notify, 
                        "Error: 'mpv' media player is not installed or not in PATH.", 
                        severity="error"
                    )
                    
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Playback Error: {e}", severity="error")
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
