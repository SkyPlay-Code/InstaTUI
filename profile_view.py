# profile_view.py
import os
from io import BytesIO
import requests
from PIL import Image
from textual import work
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Input, Label, LoadingIndicator, Static


class ProfileView(VerticalScroll):
    """The Component that searches, displays, and interacts with an Instagram Profile."""

    def compose(self):
        yield Input(placeholder="🔍 Enter username to search...", id="profile-search")
        yield LoadingIndicator(id="profile-loading")
        
        with Vertical(id="profile-card"):
            with Horizontal(id="profile-top-section"):
                yield Static("Image will appear here", id="profile-pic-container")
                with Vertical(id="profile-stats-container"):
                    yield Label("", id="profile-username")
                    yield Label("", id="profile-fullname")
                    yield Label("", id="profile-counters")
                    # View HD Avatar Button
                    yield Button("👁️ View Fullscreen HD", id="btn-view-avatar", variant="primary")
            
            yield Label("", id="profile-bio")
            yield Label("", id="profile-footer")
            
            with Horizontal(id="profile-actions"):
                yield Button("👤 Follow", id="btn-follow", variant="success")
                yield Button("🚫 Unfollow", id="btn-unfollow", variant="error")

    def on_mount(self):
        self.query_one("#profile-loading").display = False
        self.query_one("#profile-card").display = False
        self.current_target_id = None 
        self.current_pic_url = None # Caches the URL for HD rendering
        self.raw_pic_url = None     # Fallback cache for raw CDN URL

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "profile-search":
            username = event.input.value.strip()
            if username:
                self.query_one("#profile-card").display = False
                self.query_one("#profile-loading").display = True
                # Remove active focus from the input field to enable navigation bindings
                self.app.set_focus(None)
                self.fetch_profile(username)

    @work
    async def fetch_profile(self, username):
        cl = self.app.ig_client
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            
            # Wrap block-level API calls into thread executor to keep the TUI loop active and snappy
            def fetch_data():
                with self.app.api_lock:
                    user_info = cl.user_info_by_username_v1(username)
                    friendship = cl.user_friendship_v1(user_info.pk)
                return user_info, friendship

            user_info, friendship = await loop.run_in_executor(None, fetch_data)
            self.display_profile(user_info, friendship)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")
            self.hide_loading()

    def hide_loading(self) -> None:
        """Hides the loading indicator safely on the main thread and restores display state."""
        try:
            self.query_one("#profile-loading").display = False
            if self.current_target_id:
                self.query_one("#profile-card").display = True
        except Exception:
            pass

    def optimize_avatar_url(self, url: str) -> str:
        """Safely upgrades low-resolution CDN path/query parameters to high-definition."""
        if not url:
            return url
        for low_res in ["s150x150", "s240x240", "s320x320", "s480x480"]:
            if low_res in url:
                url = url.replace(low_res, "s640x640")
        return url

    def display_profile(self, user, friendship):
        self.query_one("#profile-loading").display = False
        
        self.current_target_id = user.pk
        username = getattr(user, 'username', 'Unknown')
        fullname = getattr(user, 'full_name', '')
        bio = getattr(user, 'biography', 'No bio available.')
        followers = getattr(user, 'follower_count', 0)
        following = getattr(user, 'following_count', 0)
        posts = getattr(user, 'media_count', 0)
        
        # Keep track of both raw and optimized URLs
        raw_hd_url = getattr(user, 'profile_pic_url_hd', None) or getattr(user, 'profile_pic_url', None)
        self.raw_pic_url = str(raw_hd_url) if raw_hd_url else None
        self.current_pic_url = self.optimize_avatar_url(self.raw_pic_url) if self.raw_pic_url else None

        badges = ""
        if getattr(user, 'is_verified', False): badges += "[blue]☑ Verified[/blue] "
        if getattr(user, 'is_private', False): badges += "[red]🔒 Private[/red] "
        
        if getattr(friendship, 'followed_by', False):
            badges += "[green]✦ Follows You[/green] "

        self.query_one("#profile-username", Label).update(f"[b text-title]@{username}[/] {badges}")
        self.query_one("#profile-fullname", Label).update(f"[i]{fullname}[/i]")
        self.query_one("#profile-counters", Label).update(
            f"📸 Posts: [b]{posts}[/b] | 👥 Followers: [b]{followers}[/b] | 👤 Following: [b]{following}[/b]"
        )
        self.query_one("#profile-bio", Label).update(f"\n📝 [b]Bio:[/b]\n{bio}")
        
        link = getattr(user, 'external_url', None)
        if link:
            self.query_one("#profile-footer", Label).update(f"\n🔗 [blue u]{link}[/]")
        else:
            self.query_one("#profile-footer", Label).update("")

        if self.current_pic_url:
            self.render_terminal_image(self.current_pic_url)
        else:
            self.query_one("#profile-pic-container", Static).update("[No Picture]")

        self.query_one("#profile-card").display = True

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not self.current_target_id:
            return

        if event.button.id == "btn-follow":
            self.app.notify("Sending Follow Request...")
            self.trigger_action("follow", self.current_target_id)
        
        elif event.button.id == "btn-unfollow":
            self.app.notify("Unfollowing...")
            self.trigger_action("unfollow", self.current_target_id)

        elif event.button.id == "btn-view-avatar":
            if self.current_pic_url:
                self.app.notify("Downloading HD profile picture...")
                self.play_avatar_in_terminal(self.current_pic_url, self.current_target_id)
            else:
                self.app.notify("No HD avatar URL available for this user.", severity="error")

    # ==========================================
    # 👑 MODERN ASYNC EVENT-LOOP WORKER (NO RAW OS THREADS)
    # ==========================================
    @work
    async def play_avatar_in_terminal(self, url, target_id):
        """Asynchronously handles downloads and initiates play activities on the main thread."""
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            
            # Fetch requests using loop executor to prevent UI freeze
            async def download(download_url):
                return await loop.run_in_executor(None, lambda: requests.get(download_url, timeout=10))
            
            try:
                resp = await download(url)
                resp.raise_for_status()
            except Exception as e:
                if self.raw_pic_url and url != self.raw_pic_url:
                    self.app.notify("HD URL failed, trying standard resolution...", severity="warning")
                    resp = await download(self.raw_pic_url)
                    resp.raise_for_status()
                else:
                    raise e

            # Using standard system temporary directory to guarantee absolute file write permissions
            import tempfile
            filename = f"avatar_cache_hd_{target_id}.jpg"
            path = os.path.abspath(os.path.join(tempfile.gettempdir(), filename))
            
            def write_file():
                with open(path, 'wb') as f:
                    f.write(resp.content)
            
            await loop.run_in_executor(None, write_file)
            
            # Request app to trigger GUI player
            self.app.play_media_file(path, is_video=False, cleanup=True)
            
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")

    @work
    async def trigger_action(self, action, user_id):
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            
            def make_call():
                cl = self.app.ig_client
                with self.app.api_lock:
                    if action == "follow":
                        cl.user_follow(user_id)
                    else:
                        cl.user_unfollow(user_id)

            await loop.run_in_executor(None, make_call)
            self.app.notify(f"Successfully executed: {action}!")
        except Exception as e:
            self.app.notify(f"Action failed: {e}", severity="error")

    @work
    async def render_terminal_image(self, url):
        """Generates inline block-art from the HD original using async execution."""
        try:
            import asyncio
            loop = asyncio.get_running_loop()
            
            async def download():
                return await loop.run_in_executor(None, lambda: requests.get(url, timeout=5))
            
            try:
                resp = await download()
                resp.raise_for_status()
            except Exception as e:
                if self.raw_pic_url and url != self.raw_pic_url:
                    async def download_raw():
                        return await loop.run_in_executor(None, lambda: requests.get(self.raw_pic_url, timeout=5))
                    resp = await download_raw()
                    resp.raise_for_status()
                else:
                    raise e

            def process_image():
                img = Image.open(BytesIO(resp.content)).convert("RGB")
                is_hd = getattr(self.app, 'media_quality', 'lowq') == 'hd'
                target_width = 44 if is_hd else 24 
                
                w, h = img.size
                ratio = h / w
                target_height = int(target_width * ratio / 2) 
                
                img = img.resize((target_width, target_height * 2), Image.Resampling.LANCZOS)
                ascii_art = ""
                for y in range(0, target_height * 2, 2):
                    line = ""
                    for x in range(target_width):
                        r1, g1, b1 = img.getpixel((x, y))      
                        r2, g2, b2 = img.getpixel((x, y + 1)) if y + 1 < target_height * 2 else (0, 0, 0)
                        line += f"[#{r1:02x}{g1:02x}{b1:02x} on #{r2:02x}{g2:02x}{b2:02x}]▀[/]"
                    ascii_art += line + "\n"
                return ascii_art

            ascii_art = await loop.run_in_executor(None, process_image)
            self.update_pic_container(ascii_art)
        except Exception:
            self.update_pic_container("[red]Img Failed[/red]")

    def update_pic_container(self, ascii_art: str) -> None:
        """Safely updates the picture container on the main thread."""
        try:
            self.query_one("#profile-pic-container", Static).update(ascii_art)
        except Exception:
            pass