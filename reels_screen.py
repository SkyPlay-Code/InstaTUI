import subprocess
import random
from textual.screen import Screen
from textual.widgets import OptionList, LoadingIndicator, Label, Footer, Input
from textual.containers import Vertical
from textual import work

# A pool of accounts that post 100% Reels. 
# The app will randomly pick one of these to simulate an "Explore" feed on launch!
EXPLORE_POOL = ["9gag", "pubity", "memezar", "nature", "animalsdoingthings"]

class ReelsScreen(Screen):
    """The Screen that fetches and plays Instagram Reels."""

    def compose(self):
        with Vertical(id="inbox-container"):
            yield Label("🎬 Initializing Feed...", id="inbox-header")
            yield Input(placeholder="Optional: Search a specific username here...", id="username-input")
            yield LoadingIndicator(id="loading")
            yield OptionList(id="reels-list")
        yield Footer()

    def on_mount(self):
        self.reels_data = []
        self.query_one("#reels-list").display = False
        
        # Automatically simulate an explore feed by picking a random hit page!
        random_page = random.choice(EXPLORE_POOL)
        self.fetch_reels(random_page)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Triggered ONLY if you decide to manually use the search box."""
        if event.input.id == "username-input":
            username = event.input.value.strip()
            if username:
                self.query_one("#loading").display = True
                self.query_one("#reels-list").display = False
                self.fetch_reels(username)

    @work(thread=True)
    def fetch_reels(self, username):
        """Uses the ultra-stable user_clips method."""
        cl = self.app.ig_client
        try:
            self.app.call_from_thread(
                self.query_one("#inbox-header", Label).update, f"📡 Fetching Feed (@{username})..."
            )
            
            # Find the ID of the account
            user_id = cl.user_id_from_username(username)
            
            # Fetch 15 reels from them!
            reels = cl.user_clips(user_id, amount=15)

            if not reels:
                raise Exception(f"No reels found for @{username}.")

            self.app.call_from_thread(self.populate_reels, reels)
            
        except Exception as e:
            self.app.call_from_thread(self.show_error, str(e))

    def populate_reels(self, reels):
        """Safely extracts data and populates the UI list."""
        self.reels_data = reels
        self.query_one("#loading").display = False
        
        reels_list = self.query_one("#reels-list", OptionList)
        reels_list.clear_options()
        reels_list.display = True
        
        for reel in reels:
            # Bulletproof attribute extraction
            author = getattr(reel.user, 'username', 'Unknown') if hasattr(reel, 'user') and reel.user else 'Unknown'
            caption = getattr(reel, 'caption_text', 'No caption') or "No caption"
            caption = caption.replace("\n", " ")
            
            reels_list.add_option(f"▶️ @{author} | {caption[:55]}...")
            
        self.query_one("#inbox-header", Label).update("🎬 REELS FEED (Select & Press Enter to Play!)")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Triggers when you press Enter on a Reel."""
        selected_reel = self.reels_data[event.option_index]
        video_url = None
        
        # 1. Try checking for the main video_url attribute
        if hasattr(selected_reel, 'video_url') and selected_reel.video_url:
            video_url = selected_reel.video_url
            
        # 2. If it's hidden, check the video_versions array
        elif hasattr(selected_reel, 'video_versions') and selected_reel.video_versions:
            version = selected_reel.video_versions[0]
            # Depending on instagrapi version, this could be a dict or an object
            if isinstance(version, dict):
                video_url = version.get('url')
            else:
                video_url = getattr(version, 'url', None)

        if video_url:
            self.play_video_in_terminal(video_url)
        else:
            self.show_error("Could not extract video URL from this reel.")

    def play_video_in_terminal(self, url):
        """Suspends the TUI and opens MPV in the terminal."""
        with self.app.suspend():
            print("\033[2J\033[H", end="") 
            print("🚀 LOADING REEL... (Press 'q' to exit back to TUI)")
            print("-" * 50)
            
            try:
                subprocess.run([
                    "mpv",
                    "--vo=tct", 
                    "--quiet",
                    str(url)
                ])
            except FileNotFoundError:
                print("\n❌ Error: 'mpv' not found in PATH.")
                input("Press Enter to return...")

    def show_error(self, error_msg: str):
        self.query_one("#loading").display = False
        self.query_one("#inbox-header", Label).update(f"❌ Error: {error_msg[:50]}")
