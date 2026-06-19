# reels_view.py
import os
import subprocess

from textual import work
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Label, LoadingIndicator, OptionList


class ReelsView(Vertical):
    """The Ultimate Native Reels Feed Component based on your exact source."""

    def compose(self):
        with Vertical(id="reels-container"):
            yield Label("🎬 Native Reels Feed", id="reels-header")
            
            with Horizontal(id="reels-actions"):
                # Notice we have TWO feeds now, mapped exactly to your timeline.py!
                yield Button("🚀 Fetch Explore (Discover)", id="fetch-explore-btn", variant="primary")
                yield Button("🚀 Fetch Home (Connected)", id="fetch-connected-btn", variant="primary")
            
            yield LoadingIndicator(id="reels-loading")
            yield OptionList(id="reels-list")

    def on_mount(self):
        self.query_one("#reels-loading").display = False
        self.query_one("#reels-list").display = False
        self.reels_cache = []

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("fetch-explore-btn", "fetch-connected-btn"):
            self.query_one("#reels-loading").display = True
            self.query_one("#reels-list").display = False
            for btn in self.query(Button):
                btn.disabled = True
            
            mode = "explore" if event.button.id == "fetch-explore-btn" else "connected"
            self.fetch_reels(mode)

    @work(thread=True)
    def fetch_reels(self, mode):
        cl = self.app.ig_client
        try:
            self.app.call_from_thread(self.update_status, f"📡 Hitting {mode.upper()} endpoints natively...")
            
            # Here we map directly to your `timeline.py` functions!
            if mode == "explore":
                reels = cl.explore_reels(amount=15)
            else:
                reels = cl.reels(amount=15)
            
            if not reels:
                raise Exception(f"The {mode} API returned no media items.")

            self.app.call_from_thread(self.display_reels, reels)

        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Feed Error: {str(e)[:40]}", severity="error")
            self.app.call_from_thread(self.reset_ui)

    def update_status(self, text):
        self.query_one("#reels-header").update(f"🎬 {text}")

    def reset_ui(self):
        for btn in self.query(Button):
            btn.disabled = False
        self.query_one("#reels-loading").display = False

    def display_reels(self, reels):
        self.reset_ui()
        self.reels_cache = reels
        self.update_status(f"Feed Loaded: {len(reels)} clips ready.")
        
        list_ui = self.query_one("#reels-list", OptionList)
        list_ui.clear_options()
        list_ui.display = True
        
        for r in reels:
            # We know the exact structure of Media because of your test_timeline.py dumps
            author = getattr(r.user, 'username', 'Unknown') if r.user else "Unknown"
            caption = getattr(r, 'caption_text', 'No caption') or "No caption"
            list_ui.add_option(f"▶️ @{author} | {caption.replace(chr(10), ' ')[:60]}...")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if not self.reels_cache: return
        
        selected_reel = self.reels_cache[event.option_index]
        media_pk = getattr(selected_reel, 'pk', None)
        author = getattr(selected_reel.user, 'username', 'user') if selected_reel.user else 'user'
        
        if media_pk:
            self.app.notify("Downloading Reel via native clip_download()...", timeout=3)
            self.play_downloaded_reel(media_pk, author)
        else:
            self.app.notify("No PK found for this media.", severity="error")

    @work(thread=True)
    def play_downloaded_reel(self, media_pk, author):
        cl = self.app.ig_client
        path = None
        try:
            path = cl.clip_download(media_pk, folder=".")
            with self.app.suspend():
                print("\033[2J\033[H", end="") 
                print(f"🚀 PLAYING REEL BY @{author.upper()} (Press 'q' when finished)")
                print("-" * 50)
                
                # Sixel vs TCT
                is_hd = getattr(self.app, 'media_quality', 'lowq') == 'hd'
                vo_driver = "sixel" if is_hd else "tct"
                
                cmd = f'mpv --vo={vo_driver} --quiet "{path}"'
                subprocess.run(cmd, shell=True)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Playback Error: {e}", severity="error")
        finally:
            if path and os.path.exists(path):
                os.remove(path)