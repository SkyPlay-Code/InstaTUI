# chat_screen.py
import os
import subprocess
from io import BytesIO

import requests
from PIL import Image
from textual import work
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Input, Label, LoadingIndicator, Static


class ChatScreen(Screen):
    def __init__(self, thread, **kwargs):
        super().__init__(**kwargs)
        self.thread = thread 
        self.media_cache = {} 

    def compose(self):
        title = getattr(self.thread, 'thread_title', None)
        if not title: title = ", ".join([u.username for u in self.thread.users])

        with Vertical(id="chat-main-container"):
            yield Label(f"💬 {title}", id="chat-header")
            
            with VerticalScroll(id="message-container"):
                yield LoadingIndicator(id="chat-loading")
            
            with Horizontal(id="input-container"):
                yield Input(placeholder="Msg | /image <path> | /unsend | /play <url>", id="message-input")
                yield Button("Send", id="send-btn", variant="success")
            
            with Horizontal(id="chat-footer"):
                yield Button("⬅ Back", id="back-btn", variant="error")
                yield Button("🔄 Refresh Chat", id="refresh-chat-btn", variant="primary")

    def on_mount(self):
        self.fetch_messages()

    @work(thread=True)
    def fetch_messages(self):
        try:
            self.app.call_from_thread(self.query_one("#message-container").remove_children)
            messages = self.app.ig_client.direct_messages(self.thread.id, amount=25)
            messages.reverse()
            self.app.call_from_thread(self.display_messages, messages)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Load error: {e}", severity="error")

    def format_timestamp(self, msg):
        if getattr(msg, 'timestamp', None):
            try: return msg.timestamp.astimezone().strftime("%I:%M %p")
            except: pass
        return "??:??"

    def get_media_url(self, msg):
        """Pulls the exact media URL using Pydantic attributes from types.py."""
        url, is_video = None, False

        # 1. Standard Media (Photos, Videos, Voice)
        if getattr(msg, 'media', None):
            if getattr(msg.media, 'video_url', None):
                url, is_video = msg.media.video_url, True
            elif getattr(msg.media, 'audio_url', None):
                url, is_video = msg.media.audio_url, False # Usually m4a voice note
            elif getattr(msg.media, 'thumbnail_url', None):
                url, is_video = msg.media.thumbnail_url, False
                
        # 2. Visual Media (Vanishing/Disappearing photos and videos)
        elif getattr(msg, 'visual_media', None) and getattr(msg.visual_media, 'media', None):
            vm = msg.visual_media.media
            if getattr(vm, 'video_versions', None):
                url, is_video = vm.video_versions[0].url, True
            elif getattr(vm, 'image_versions2', None) and vm.image_versions2.candidates:
                url, is_video = vm.image_versions2.candidates[0].url, False
                
        # 3. Clips/Reels
        elif getattr(msg, 'clip', None) and getattr(msg.clip, 'video_url', None):
            url, is_video = msg.clip.video_url, True
            
        # 4. Shared Posts (XMA)
        elif getattr(msg, 'xma_share', None):
            url = getattr(msg.xma_share, 'video_url', None) or getattr(msg.xma_share, 'preview_url', None)

        return str(url) if url else None, is_video

    def display_messages(self, messages):
        container = self.query_one("#message-container")
        container.remove_children() 
        my_id = str(self.app.ig_client.user_id)
        
        for msg in messages:
            is_me = str(msg.user_id) == my_id
            time_str = self.format_timestamp(msg)
            
            sender_prefix = f"[{time_str}] [ME]" if is_me else f"[{time_str}] [THEM]"
            classes = "msg-me" if is_me else "msg-them"
            
            if msg.item_type == "text":
                container.mount(Label(f"{sender_prefix}: {msg.text}", classes=classes, markup=False))
            else:
                url, is_video = self.get_media_url(msg)
                
                if url:
                    self.media_cache[msg.id] = (url, is_video)
                    
                    if is_video:
                        container.mount(Label(f"{sender_prefix}: 🎬 Video / Voice", classes=classes))
                        container.mount(Button("▶️ Play Media", id=f"view_vid_{msg.id}", variant="success"))
                    else:
                        container.mount(Label(f"{sender_prefix}: 📷 Photo", classes=classes))
                        container.mount(Button("👁️ View Photo", id=f"view_pic_{msg.id}", variant="primary"))
                else:
                    container.mount(Label(f"{sender_prefix}: [{msg.item_type.upper()}]", classes=classes, markup=False))
            
        container.scroll_end(animate=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back-btn":
            self.app.pop_screen()
            
        elif event.button.id == "refresh-chat-btn":
            self.query_one("#message-container").mount(Label("🔄 Refreshing...", classes="msg-system"))
            self.fetch_messages()
            
        elif event.button.id == "send-btn":
            self.process_input()
            
        elif event.button.id and event.button.id.startswith("view_pic_"):
            msg_id = event.button.id.replace("view_pic_", "")
            media_data = self.media_cache.get(msg_id)
            if media_data:
                event.button.label = "Loading pixels..."
                event.button.disabled = True
                self.render_chat_image(media_data[0], msg_id)
                
        elif event.button.id and event.button.id.startswith("view_vid_"):
            msg_id = event.button.id.replace("view_vid_", "")
            media_data = self.media_cache.get(msg_id)
            if media_data:
                self.launch_mpv_video(media_data[0])

    def process_input(self):
        input_widget = self.query_one("#message-input", Input)
        txt = input_widget.value.strip()
        if not txt: return  
        input_widget.value = "" 
        
        if txt.lower() == "/unsend":
            self.query_one("#message-container").mount(Label(f"🧹 Sweeping last message...", classes="msg-system"))
            self.run_unsend()
        elif txt.lower().startswith("/image "):
            path = txt[7:].strip().strip('"').strip("'")
            if not os.path.exists(path): return
            self.query_one("#message-container").mount(Label(f"[NOW] [ME]: 📷 Uploading...", classes="msg-me"))
            self.run_send_photo(path)
        elif txt.lower().startswith("/play "):
            url = txt[6:].strip()
            self.launch_mpv_video(url)
        else:
            self.query_one("#message-container").mount(Label(f"[NOW] [ME]: {txt}", classes="msg-me", markup=False))
            self.run_send_text(txt)
            self.query_one("#message-container").scroll_end(animate=True)

    @work(thread=True)
    def run_send_text(self, text):
        try: self.app.ig_client.direct_send(text, thread_ids=[self.thread.id])
        except Exception as e: self.app.call_from_thread(self.app.notify, f"Send Error: {e}", severity="error")

    @work(thread=True)
    def run_send_photo(self, path):
        try: self.app.ig_client.direct_send_photo(path, thread_ids=[self.thread.id])
        except Exception as e: self.app.call_from_thread(self.app.notify, f"Upload Error: {e}", severity="error")

    @work(thread=True)
    def run_unsend(self):
        cl = self.app.ig_client
        my_id = str(cl.user_id)
        try:
            messages = cl.direct_messages(self.thread.id, amount=15)
            last_msg = next((m for m in messages if str(m.user_id) == my_id), None)
            if last_msg:
                cl.private_request(f"direct_v2/threads/{self.thread.id}/items/{last_msg.id}/delete/")
                self.app.call_from_thread(self.fetch_messages) 
                self.app.call_from_thread(self.app.notify, "✅ Message unsent.")
        except: pass

    @work(thread=True)
    def play_reel_from_url(self, url):
            cl = self.app.ig_client
            path = None
            try:
                media_pk = cl.media_pk_from_url(url)
                path = cl.video_download(media_pk, folder=".")
                with self.app.suspend():
                    print("\033[2J\033[H", end="") 
                    print("🚀 PLAYING REEL LINK (Press 'q' when finished)")
                    print("-" * 50)
                    
                    # Sixel vs TCT
                    is_hd = getattr(self.app, 'media_quality', 'lowq') == 'hd'
                    vo_driver = "sixel" if is_hd else "tct"
                    
                    cmd = f'mpv --vo={vo_driver} --quiet "{path}"'
                    subprocess.run(cmd, shell=True)
            except Exception as e:
                self.app.call_from_thread(self.app.notify, f"Player error: {e}", severity="error")
            finally:
                if path and os.path.exists(path):
                    os.remove(path)
    
    def launch_mpv_video(self, url):
        """Plays raw video message URLs using the configured terminal driver."""
        with self.app.suspend():
            print("\033[2J\033[H", end="") 
            print("🚀 PLAYING CHAT MEDIA (Press 'q' to return)")
            print("-" * 50)
            
            # Sixel vs TCT
            is_hd = getattr(self.app, 'media_quality', 'lowq') == 'hd'
            vo_driver = "sixel" if is_hd else "tct"
            
            cmd = f'mpv --vo={vo_driver} --quiet "{url}"'
            subprocess.run(cmd, shell=True)

    @work(thread=True)
    def render_chat_image(self, url, msg_id):
        try:
            resp = requests.get(url, timeout=10)
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            
            target_width = 45
            w, h = img.size
            target_height = int(target_width * (h / w) / 2) 
            
            img = img.resize((target_width, target_height * 2), Image.Resampling.LANCZOS)
            ascii_art = "\n"
            for y in range(0, target_height * 2, 2):
                line = ""
                for x in range(target_width):
                    r1, g1, b1 = img.getpixel((x, y))      
                    r2, g2, b2 = img.getpixel((x, y + 1)) if y + 1 < target_height * 2 else (0, 0, 0)
                    line += f"[#{r1:02x}{g1:02x}{b1:02x} on #{r2:02x}{g2:02x}{b2:02x}]▀[/]"
                ascii_art += line + "\n"
            self.app.call_from_thread(self.inject_image_into_chat, ascii_art, msg_id)
        except: pass

    def inject_image_into_chat(self, ascii_art, msg_id):
        btn = self.query_one(f"#view_pic_{msg_id}")
        btn.styles.display = "none"
        self.query_one("#message-container").mount(Static(ascii_art), after=btn)
        self.query_one("#message-container").scroll_end(animate=True)
