# profile_view.py
import os
import subprocess
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
                    # --- NEW: View HD Avatar Button ---
                    yield Button("👁️ View HD Avatar", id="btn-view-avatar", variant="primary")
            
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

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "profile-search":
            username = event.input.value.strip()
            if username:
                self.query_one("#profile-card").display = False
                self.query_one("#profile-loading").display = True
                self.fetch_profile(username)

    @work(thread=True)
    def fetch_profile(self, username):
        cl = self.app.ig_client
        try:
            user_info = cl.user_info_by_username(username)
            friendship = cl.user_friendship_v1(user_info.pk)
            self.app.call_from_thread(self.display_profile, user_info, friendship)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {e}", severity="error")
            self.app.call_from_thread(lambda: setattr(self.query_one("#profile-loading"), 'display', False))

    def display_profile(self, user, friendship):
        self.query_one("#profile-loading").display = False
        
        self.current_target_id = user.pk
        username = getattr(user, 'username', 'Unknown')
        fullname = getattr(user, 'full_name', '')
        bio = getattr(user, 'biography', 'No bio available.')
        followers = getattr(user, 'follower_count', 0)
        following = getattr(user, 'following_count', 0)
        posts = getattr(user, 'media_count', 0)
        self.current_pic_url = getattr(user, 'profile_pic_url', None)

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

        # --- NEW: View HD Avatar Action ---
        elif event.button.id == "btn-view-avatar":
            if self.current_pic_url:
                self.app.notify("Downloading HD profile picture...")
                self.play_avatar_in_terminal(self.current_pic_url)

    @work(thread=True)
    def play_avatar_in_terminal(self, url):
        path = None
        try:
            resp = requests.get(url, timeout=5)
            filename = f"avatar_cache_{self.current_target_id}.jpg"
            path = os.path.join(".", filename)
            
            with open(path, 'wb') as f:
                f.write(resp.content)
                
            with self.app.suspend():
                print("\033[2J\033[H", end="") 
                print(f"🚀 VIEWING AVATAR (Press 'q' to return)")
                print("-" * 50)
                
                # Check global quality toggle setting!
                is_hd = getattr(self.app, 'media_quality', 'lowq') == 'hd'
                vo_driver = "sixel" if is_hd else "tct"
                
                # MPV loads our local image perfectly inside the terminal!
                cmd = f'mpv --vo={vo_driver} --quiet --image-display-duration=inf "{path}"'
                subprocess.run(cmd, shell=True)
                
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {e}", severity="error")
        finally:
            if path and os.path.exists(path):
                os.remove(path)

    @work(thread=True)
    def trigger_action(self, action, user_id):
        try:
            cl = self.app.ig_client
            if action == "follow":
                cl.user_follow(user_id)
            else:
                cl.user_unfollow(user_id)
            self.app.call_from_thread(self.app.notify, f"Successfully executed: {action}!")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Action failed: {e}", severity="error")

    @work(thread=True)
    def render_terminal_image(self, url):
        """Generates inline block-art. Resolution increases if HD mode is toggled!"""
        try:
            resp = requests.get(url, timeout=5)
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            
            # --- NEW: Dynamic Resolution Toggling ---
            # If globally set to HD, double the inline ANSI resolution!
            is_hd = getattr(self.app, 'media_quality', 'lowq') == 'hd'
            target_width = 48 if is_hd else 28 
            
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
            self.app.call_from_thread(self.query_one("#profile-pic-container", Static).update, ascii_art)
        except Exception as e:
            self.app.call_from_thread(self.query_one("#profile-pic-container", Static).update, "[red]Img Failed[/red]")