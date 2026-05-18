# ghost_view.py
import os
import requests
import subprocess
from textual.widgets import OptionList, LoadingIndicator, Label, Button, Input
from textual.containers import Vertical, Horizontal
from textual import work

class GhostView(Vertical):
    """Anonymously view 24h Stories and Profile Highlights."""

    def compose(self):
        with Vertical(id="ghost-container"):
            yield Label("👻 The Ghost Viewer (100% Anonymous)", id="ghost-header", classes="section-header")
            yield Label("💡 HACKER TIP: Use Ctrl+V (or Ctrl+Shift+V) to Paste!", classes="ghost-tip")
            
            with Horizontal(classes="action-row"):
                yield Input(placeholder="Target Username (e.g. instagram)...", id="ghost-target")
                yield Button("🔍 Scan Profile", id="ghost-scan-btn", variant="primary")
            
            yield LoadingIndicator(id="ghost-loading")
            
            # Two-panel layout: Categories on the left, Story Frames on the right
            with Horizontal(id="ghost-panels"):
                with Vertical(classes="ghost-panel"):
                    yield Label("📂 Available Folders", classes="panel-title")
                    yield OptionList(id="category-list")
                
                with Vertical(classes="ghost-panel"):
                    yield Label("🎞️ Story Frames", id="frame-panel-title", classes="panel-title")
                    yield OptionList(id="frame-list")

    def on_mount(self):
        self.query_one("#ghost-loading").display = False
        self.query_one("#ghost-panels").display = False
        
        # State Management
        self.active_stories = []
        self.highlights_map = {} 
        self.category_keys = []  
        self.current_frames = [] 

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "ghost-target":
            self.query_one("#ghost-scan-btn").press()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ghost-scan-btn":
            username = self.query_one("#ghost-target").value.strip()
            if username:
                self.query_one("#ghost-scan-btn").disabled = True
                self.query_one("#ghost-panels").display = False
                self.query_one("#ghost-loading").display = True
                self.fetch_target_data(username)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        # LEFT PANEL CLICK: Load Folder
        if event.option_list.id == "category-list":
            selected_key = self.category_keys[event.option_index]
            self.load_frames_for_category(selected_key)
            
        # RIGHT PANEL CLICK: Play Story!
        elif event.option_list.id == "frame-list":
            if not self.current_frames: return
            selected_frame = self.current_frames[event.option_index]
            self.play_ghost_frame(selected_frame)

    # ===============================
    # WORKERS & LOGIC
    # ===============================

    @work(thread=True)
    def fetch_target_data(self, username):
        cl = self.app.ig_client
        try:
            self.app.call_from_thread(self.query_one("#ghost-header").update, f"👻 Ghosting @{username} (Finding ID...)")
            user_id = cl.user_id_from_username(username)
            
            # Fetch active 24h stories
            self.app.call_from_thread(self.query_one("#ghost-header").update, "👻 Fetching 24h Stories...")
            active = cl.user_stories(user_id)
            
            # Fetch highlight tray
            self.app.call_from_thread(self.query_one("#ghost-header").update, "👻 Fetching Profile Highlights...")
            highlights = cl.user_highlights(user_id)
            
            self.app.call_from_thread(self.display_categories, active, highlights)

        except Exception as e:
            err = str(e)
            if "private" in err.lower() or "not authorized" in err.lower():
                self.app.call_from_thread(self.app.notify, "❌ Cannot ghost private profiles! (You don't follow them)", severity="error")
            else:
                self.app.call_from_thread(self.app.notify, f"Error: {err}", severity="error")
            self.app.call_from_thread(self.reset_ui)

    def display_categories(self, active_stories, highlights):
        self.active_stories = active_stories
        self.highlights_map = {hl.pk: hl for hl in highlights}
        self.category_keys = []
        
        self.reset_ui()
        self.query_one("#ghost-panels").display = True
        
        cat_list = self.query_one("#category-list", OptionList)
        cat_list.clear_options()
        self.query_one("#frame-list", OptionList).clear_options()
        self.query_one("#frame-panel-title", Label).update("🎞️ Select a Folder ⬅️")

        cat_list.add_option(f"🟢 Active 24h Stories ({len(active_stories)})")
        self.category_keys.append("active")

        for hl in highlights:
            title = getattr(hl, 'title', 'Highlight')
            count = getattr(hl, 'media_count', '?')
            cat_list.add_option(f"⭐ {title} ({count})")
            self.category_keys.append(hl.pk)
            
        self.query_one("#ghost-header").update("👻 Target Acquired (Invisible Mode ACTIVE)")

    @work(thread=True)
    def load_frames_for_category(self, key):
        frames = []
        panel_title = ""
        cl = self.app.ig_client
        
        try:
            if key == "active":
                frames = self.active_stories
                panel_title = f"🎞️ Active Stories"
            else:
                hl = self.highlights_map[key]
                panel_title = f"🎞️ '{hl.title}'"
                self.app.call_from_thread(self.query_one("#frame-panel-title").update, "⏳ Opening Highlight Folder...")
                
                # Fetch highlight content dynamically
                full_hl = cl.highlight_info(hl.pk)
                frames = getattr(full_hl, 'items', [])
                self.highlights_map[key] = full_hl 
                
            self.app.call_from_thread(self.display_frames, frames, panel_title)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Failed to load folder: {e}", severity="error")

    def display_frames(self, frames, title):
        self.current_frames = frames
        self.query_one("#frame-panel-title").update(title)
        
        frame_list = self.query_one("#frame-list", OptionList)
        frame_list.clear_options()
        
        if not frames:
            frame_list.add_option("Folder is empty.")
            return

        for f in frames:
            is_video = getattr(f, 'media_type', 1) == 2
            icon = "🎥 Video" if is_video else "📸 Photo"
            
            # Safe timestamp check from types.py
            if getattr(f, 'taken_at', None):
                time_str = f.taken_at.astimezone().strftime("%Y-%m-%d %I:%M %p")
            else:
                time_str = "Unknown Date"
                
            frame_list.add_option(f"{icon} | {time_str}")

    @work(thread=True)
    def play_ghost_frame(self, story):
        path = None
        is_video = getattr(story, 'media_type', 1) == 2
        
        try:
            url = getattr(story, 'video_url', None) if is_video else getattr(story, 'thumbnail_url', None)
            
            if not url:
                self.app.call_from_thread(self.app.notify, "Missing CDN Link.", severity="error")
                return

            self.app.call_from_thread(self.app.notify, "Stealth Downloading...", timeout=3)
            
            ext = ".mp4" if is_video else ".jpg"
            filename = f"ghost_cache_{story.pk}{ext}"
            path = os.path.join(".", filename)
            
            # The True Ghost method: Raw HTTP GET directly from Meta's CDNs
            r = requests.get(url, stream=True, timeout=10)
            if r.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in r.iter_content(1024):
                        f.write(chunk)
            else:
                raise Exception(f"CDN Returned {r.status_code}")
            
            # Play locally in the terminal with TCT
            with self.app.suspend():
                print("\033[2J\033[H", end="") 
                print("👻 GHOST VIEW ACTIVE (You are completely invisible)")
                print("Press 'q' at any time to return to the Dashboard.")
                print("-" * 50)
                
                # --keep-open ensures MPV pauses on the last frame so photos don't vanish instantly!
                cmd = ["mpv", "--vo=tct", "--quiet", "--keep-open=yes", str(path)]
                subprocess.run(cmd)
                    
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Stealth View Error: {e}", severity="error")
        finally:
            if path and os.path.exists(path):
                os.remove(path)

    def reset_ui(self):
        self.query_one("#ghost-scan-btn").disabled = False
        self.query_one("#ghost-loading").display = False
