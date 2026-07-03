# ghost_view.py
import os
import shutil
import subprocess
import sys
import threading
import time

import requests
from textual import work
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Input, Label, LoadingIndicator, OptionList


class GhostView(Vertical):
    """Anonymously view 24h Stories and Profile Highlights."""

    # Set up bindings so pressing 'q' shows in the footer/helps with navigation
    BINDINGS = [
        Binding("q", "quit_viewer", "Stop Player / Back to Menu", show=True),
    ]

    def compose(self):
        with Vertical(id="ghost-container"):
            yield Label(
                "👻 The Ghost Viewer (100% Anonymous)",
                id="ghost-header",
                classes="section-header",
            )
            yield Label(
                "💡 HACKER TIP: Use Ctrl+V (or Ctrl+Shift+V) to Paste!",
                classes="ghost-tip",
            )

            with Horizontal(classes="action-row"):
                yield Input(
                    placeholder="Target Username (e.g. zuck)...", id="ghost-target"
                )
                yield Button("🔍 Scan Profile", id="ghost-scan-btn", variant="primary")

            yield LoadingIndicator(id="ghost-loading")

            with Horizontal(id="ghost-panels"):
                with Vertical(classes="ghost-panel"):
                    yield Label("📂 Available Folders", classes="panel-title")
                    yield OptionList(id="category-list")

                with Vertical(classes="ghost-panel"):
                    yield Label(
                        "🎞️ Story Frames", id="frame-panel-title", classes="panel-title"
                    )
                    yield OptionList(id="frame-list")

    def on_mount(self):
        self.query_one("#ghost-loading").display = False
        self.query_one("#ghost-panels").display = False

        self.active_stories = []
        self.highlights_map = {}
        self.category_keys = []
        self.current_frames = []

        # Track the active external player process so we can terminate it
        self.current_player_process = None

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
        # Left Panel (Folders)
        if event.option_list.id == "category-list":
            selected_key = self.category_keys[event.option_index]
            self.load_frames_for_category(selected_key)

        # Right Panel (Frames)
        elif event.option_list.id == "frame-list":
            # FIXED: Avoid IndexError when selecting the "Folder is empty" message
            if not self.current_frames or event.option_index >= len(
                self.current_frames
            ):
                return
            selected_frame = self.current_frames[event.option_index]
            self.play_ghost_frame(selected_frame)

    @work(thread=True)
    def fetch_target_data(self, username):
        cl = self.app.ig_client
        try:
            self.app.call_from_thread(
                self.query_one("#ghost-header").update,
                f"👻 Ghosting @{username} (Finding ID...)",
            )

            # Wrapped API operations with the global thread lock
            with self.app.api_lock:
                user_id = cl.user_id_from_username(username)

            self.app.call_from_thread(
                self.query_one("#ghost-header").update, "👻 Fetching 24h Stories..."
            )
            with self.app.api_lock:
                active = cl.user_stories(user_id)

            self.app.call_from_thread(
                self.query_one("#ghost-header").update,
                "👻 Fetching Profile Highlights...",
            )
            with self.app.api_lock:
                highlights = cl.user_highlights(user_id)

            self.app.call_from_thread(self.display_categories, active, highlights)

        except Exception as e:
            err = str(e)
            if "private" in err.lower() or "not authorized" in err.lower():
                self.app.call_from_thread(
                    self.app.notify,
                    "❌ Cannot ghost private profiles!",
                    severity="error",
                )
            else:
                self.app.call_from_thread(
                    self.app.notify, f"Error: {err}", severity="error"
                )
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
            title = getattr(hl, "title", "Highlight")
            count = getattr(hl, "media_count", "?")
            cat_list.add_option(f"⭐ {title} ({count})")
            self.category_keys.append(hl.pk)

        self.query_one("#ghost-header").update(
            "👻 Target Acquired (Invisible Mode ACTIVE)"
        )

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
                self.app.call_from_thread(
                    self.query_one("#frame-panel-title").update,
                    "⏳ Opening Highlight Folder...",
                )

                # Wrapped API interaction with the thread lock
                with self.app.api_lock:
                    full_hl = cl.highlight_info(hl.pk)
                frames = getattr(full_hl, "items", [])
                self.highlights_map[key] = full_hl

            self.app.call_from_thread(self.display_frames, frames, panel_title)
        except Exception as e:
            self.app.call_from_thread(
                self.app.notify, f"Failed to load folder: {e}", severity="error"
            )

    def display_frames(self, frames, title):
        self.current_frames = frames
        self.query_one("#frame-panel-title").update(title)

        frame_list = self.query_one("#frame-list", OptionList)
        frame_list.clear_options()

        if not frames:
            frame_list.add_option("Folder is empty.")
            return

        for f in frames:
            is_video = getattr(f, "media_type", 1) == 2
            icon = "🎥 Video" if is_video else "📸 Photo"

            if getattr(f, "taken_at", None):
                time_str = f.taken_at.astimezone().strftime("%Y-%m-%d %I:%M %p")
            else:
                time_str = "Unknown Time"

            frame_list.add_option(f"{icon} | {time_str}")

    @work(thread=True)
    def play_ghost_frame(self, story):
        path = None
        is_video = getattr(story, "media_type", 1) == 2
        try:
            media_url = story.video_url if is_video else story.thumbnail_url
            if not media_url:
                raise ValueError("Story media URL is empty or unavailable.")

            url = str(media_url).strip()
            self.app.call_from_thread(
                self.app.notify, "Stealth Downloading...", timeout=3
            )

            ext = ".mp4" if is_video else ".jpg"
            path = os.path.join(".", f"ghost_cache_{story.pk}{ext}")

            r = requests.get(url, stream=True, timeout=15)
            r.raise_for_status()  # Ensure we download successfully before playing

            with open(path, "wb") as f:
                for chunk in r.iter_content(2048):
                    f.write(chunk)

            self.app.call_from_thread(self.app.notify, "Launching player...", timeout=2)

            # Play directly in this background thread. This keeps the file intact
            # while the player is open, keeping the Textual main thread fully responsive.
            self._run_external_player(path, is_video)

        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {e}", severity="error")
        finally:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    def _run_external_player(self, path, is_video):
        """Launches an external player to display media, prioritizing robust CLI viewers."""
        # Find available media player
        candidates = (
            ["mpv", "vlc", "ffplay"]
            if is_video
            else ["mpv", "feh", "sxiv", "viewnior", "display"]
        )

        chosen_player = None
        for p in candidates:
            if shutil.which(p):
                chosen_player = p
                break

        try:
            if chosen_player:
                cmd = [chosen_player, path]
                if chosen_player == "mpv":
                    cmd.append("--title=Ghost Viewer")
                    if not is_video:
                        cmd.append(
                            "--image-display-duration=inf"
                        )  # Do not auto-close images

                self.current_player_process = subprocess.Popen(cmd)
                self.current_player_process.wait()
            else:
                # System-specific default fallback
                if sys.platform.startswith("win"):
                    os.startfile(path)
                    # Because os.startfile is non-blocking, we sleep briefly
                    # so the viewer can open the file before it is deleted.
                    time.sleep(8)
                elif sys.platform == "darwin":
                    # Use -W flag to wait until the application is closed
                    self.current_player_process = subprocess.Popen(["open", "-W", path])
                    self.current_player_process.wait()
                else:  # Linux
                    self.current_player_process = subprocess.Popen(["xdg-open", path])
                    time.sleep(8)
        except Exception as e:
            raise RuntimeError(f"Could not launch player: {e}")
        finally:
            self.current_player_process = None

    def on_key(self, event) -> None:
        """Intercepts key presses bubbling up from focused child lists."""
        if event.key == "q":
            event.stop()
            self.action_quit_viewer()

    def action_quit_viewer(self) -> None:
        """Triggered by pressing 'q'. Terminates the active player, or returns to main menu."""
        if self.current_player_process:
            try:
                self.current_player_process.terminate()
                self.app.notify("Playback stopped.")
            except Exception:
                pass
            self.current_player_process = None
        else:
            # Navigate back to your app's main menu/screen
            if len(self.app.screen_stack) > 1:
                self.app.pop_screen()
            elif hasattr(self.app, "show_main_menu"):
                self.app.show_main_menu()
            else:
                self.app.notify("Already at main menu / No back transition defined.")

    def reset_ui(self):
        self.query_one("#ghost-scan-btn").disabled = False
        self.query_one("#ghost-loading").display = False
