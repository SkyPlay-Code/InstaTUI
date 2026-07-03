import os
import re
from io import BytesIO
import requests
import datetime
from PIL import Image
from textual.screen import Screen
from textual.widgets import Input, Button, Label, LoadingIndicator, Static
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual import work
from rich.markup import escape  # Safeguards against bracket-induced crashes

from reaction_screen import ReactionScreen


class ChatActionButton(Button):
    """Custom Button subclass to carry action metadata without breaking CSS ID rules."""
    def __init__(self, label: str, action_type: str, msg_id: str, **kwargs):
        super().__init__(label, **kwargs)
        self.action_type = action_type
        self.msg_id = msg_id


class ChatScreen(Screen):

    def __init__(self, thread, **kwargs):
        super().__init__(**kwargs)
        self.thread = thread 
        self.media_cache = {} 
        self.messages_cache = {} 
        self.reply_target_msg = None 

    def compose(self):
        title = getattr(self.thread, 'thread_title', None)
        if not title:
            usernames = [u.username for u in getattr(self.thread, 'users', []) if getattr(u, 'username', None)]
            title = ", ".join(usernames) if usernames else "Direct Message"

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
            # Querying DOM from background threads is unsafe. 
            # We fetch first, then clear & reload purely on the main thread inside display_messages.
            messages = self.app.ig_client.direct_messages(self.thread.id, amount=20)
            messages.reverse()
            self.app.call_from_thread(self.display_messages, messages)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Load error: {e}", severity="error")

    def format_timestamp(self, msg):
        ts = getattr(msg, 'timestamp', None)
        if ts:
            try:
                if hasattr(ts, 'astimezone'):
                    return ts.astimezone().strftime("%I:%M %p")
                
                # Check for Unix float timestamp (handling milliseconds fallback)
                ts_val = float(ts)
                if ts_val > 1e11:
                    ts_val /= 1000.0
                dt = datetime.datetime.fromtimestamp(ts_val, datetime.timezone.utc)
                return dt.astimezone().strftime("%I:%M %p")
            except:
                pass
        return "??:??"

    def extract_image_url(self, msg):
        try:
            msg_data = str(msg.dict() if hasattr(msg, 'dict') else vars(msg))
            urls = re.findall(r'(https?://[^\s\'"]+\.jpg[^\s\'"]*)', msg_data)
            if urls: return urls[0].replace('\\u0026', '&') 
        except: pass
        return None

    def display_messages(self, messages):
        container = self.query_one("#message-container")
        container.remove_children() 
        my_id = str(self.app.ig_client.user_id)
        
        self.messages_cache = {msg.id: msg for msg in messages}
        
        widgets_to_mount = []
        for msg in messages:
            is_me = str(msg.user_id) == my_id
            time_str = self.format_timestamp(msg)
            
            reactions_str = ""
            if getattr(msg, 'reactions', None) and msg.reactions.emojis:
                unique_emojis = list(set([r.emoji for r in msg.reactions.emojis]))
                reactions_str = f" [dim][{' '.join(unique_emojis)}][/dim]"
            
            sender_prefix = f"[{time_str}] [ME]" if is_me else f"[{time_str}] [THEM]"
            classes = "msg-me" if is_me else "msg-them"
            
            quote_str = ""
            if getattr(msg, 'reply', None) and msg.reply:
                quoted_sender = "You" if str(msg.reply.user_id) == my_id else "Them"
                quoted_text = msg.reply.text if msg.reply.text else "[Media]"
                # Escaped to prevent styling system crashes on nested quotes
                quote_str = f"\n  [dim]↳ Quoting {quoted_sender}: '{escape(quoted_text[:20])}...'[/dim]"
            
            row_children = []
            
            # Escape actual user input to avoid rich markup injection/crash exceptions
            escaped_text = escape(msg.text) if msg.text else ""

            if msg.item_type == "text":
                row_children.append(Label(f"{sender_prefix}: {escaped_text}{reactions_str}{quote_str}", classes=classes, markup=True))
            elif msg.item_type == "media":
                url = self.extract_image_url(msg)
                if url:
                    self.media_cache[msg.id] = url
                    row_children.append(Label(f"{sender_prefix}: 📷 Photo{reactions_str}{quote_str}", classes=classes))
                    row_children.append(ChatActionButton("👁️ Photo", action_type="view_pic", msg_id=msg.id, variant="primary", classes="msg-action-btn"))
                else:
                    row_children.append(Label(f"{sender_prefix}: 📷 [Media Blocked]{reactions_str}{quote_str}", classes=classes))
            else:
                row_children.append(Label(f"{sender_prefix}: [{msg.item_type.upper()}]{reactions_str}{quote_str}", classes=classes, markup=True))
            
            # Action buttons carry contextual properties instead of validation-unsafe CSS IDs
            row_children.append(ChatActionButton("😀", action_type="react", msg_id=msg.id, classes="msg-action-btn"))
            row_children.append(ChatActionButton("💬", action_type="reply", msg_id=msg.id, classes="msg-action-btn"))
            
            widgets_to_mount.append(Horizontal(*row_children, classes="msg-row"))
            
        container.mount(*widgets_to_mount)
        container.scroll_end(animate=False)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        
        if button.id == "back-btn":
            self.app.pop_screen()
            
        elif button.id == "refresh-chat-btn":
            self.query_one("#message-container").mount(Label("🔄 Refreshing...", classes="msg-system"))
            self.fetch_messages()
            
        elif button.id == "send-btn":
            self.process_input()
            
        elif isinstance(button, ChatActionButton):
            if button.action_type == "view_pic":
                url = self.media_cache.get(button.msg_id)
                if url:
                    button.label = "Loading..."
                    button.disabled = True
                    self.render_chat_image(url, button)
                    
            elif button.action_type == "react":
                self.trigger_reaction_picker(button.msg_id)
                
            elif button.action_type == "reply":
                self.trigger_reply_mode(button.msg_id)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Allows submitting messages by pressing Enter inside the input box."""
        if event.input.id == "message-input":
            self.process_input()

    def trigger_reaction_picker(self, msg_id):
        """Pops up the custom emoji input modal."""
        def callback(emoji):
            if emoji:
                self.app.notify(f"Reacting with {emoji}...")
                self.run_send_reaction(msg_id, emoji)
                
        self.app.push_screen(ReactionScreen(), callback)

    @work(thread=True)
    def run_send_reaction(self, msg_id, emoji):
        try:
            self.app.ig_client.direct_send_reaction(
                thread_id=self.thread.id,
                message_id=msg_id,
                emoji=emoji
            )
            self.app.call_from_thread(self.fetch_messages) 
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Reaction failed: {e}", severity="error")

    def trigger_reply_mode(self, msg_id):
        target_msg = self.messages_cache.get(msg_id)
        if target_msg:
            self.reply_target_msg = target_msg
            sender_name = "You" if target_msg.user_id == str(self.app.ig_client.user_id) else "Them"
            preview = target_msg.text if target_msg.text else "[Media]"
            
            input_widget = self.query_one("#message-input", Input)
            input_widget.placeholder = f"Replying to {sender_name}: '{preview[:15]}...' (Type /cancel to abort)"
            input_widget.focus()

    def process_input(self):
        input_widget = self.query_one("#message-input", Input)
        txt = input_widget.value.strip()
        if not txt: return  
        input_widget.value = "" 
        
        if txt.lower() == "/cancel" and self.reply_target_msg:
            self.reply_target_msg = None
            input_widget.placeholder = "Msg | /unsend | /play <url>"
            self.app.notify("Reply canceled.")
            return

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
            self.app.notify("Downloading reel temporarily for proper rendering...")
            self.play_reel_from_url(url)
            
        elif self.reply_target_msg:
            self.query_one("#message-container").mount(Label(f"[NOW] [ME]: Replying...", classes="msg-me", markup=False))
            self.run_send_reply(txt, self.reply_target_msg)
            self.reply_target_msg = None
            input_widget.placeholder = "Msg | /unsend | /play <url>"
            
        else:
            self.query_one("#message-container").mount(Label(f"[NOW] [ME]: {escape(txt)}", classes="msg-me", markup=True))
            self.run_send_text(txt)
            self.query_one("#message-container").scroll_end(animate=True)

    @work(thread=True)
    def run_send_text(self, text):
        try: self.app.ig_client.direct_send(text, thread_ids=[self.thread.id])
        except Exception as e: self.app.call_from_thread(self.app.notify, f"Send Error: {e}", severity="error")

    @work(thread=True)
    def run_send_reply(self, text, reply_to_msg):
        try:
            self.app.ig_client.direct_send(
                text, 
                thread_ids=[self.thread.id], 
                reply_to_message=reply_to_msg
            )
            self.app.call_from_thread(self.fetch_messages)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Reply Error: {e}", severity="error")

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
            else:
                self.app.call_from_thread(self.app.notify, "No messages to unsend.", severity="warning")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Unsend error: {e}", severity="error")

    def play_reel_from_url(self, url):
        self.app.play_media_file(url, is_video=True)

    def launch_mpv_video(self, url):
        self.app.play_media_file(url, is_video=True)

    @work(thread=True)
    def render_chat_image(self, url, button: ChatActionButton):
        """Fetches the image, constructs ASCII art and hands it to the main thread."""
        try:
            resp = requests.get(url, timeout=5)
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
            
            self.app.call_from_thread(self.inject_image_into_chat, ascii_art, button)
        except Exception as e:
            # Re-enable the button if an error occurs so the interface doesn't hang
            self.app.call_from_thread(self.app.notify, f"Render error: {e}", severity="error")
            self.app.call_from_thread(self.reset_image_button, button)

    def inject_image_into_chat(self, ascii_art, button: ChatActionButton):
        """Replaces the viewing button with the rendered ASCII art."""
        button.styles.display = "none"
        self.query_one("#message-container").mount(Static(ascii_art), after=button)
        self.query_one("#message-container").scroll_end(animate=True)

    def reset_image_button(self, button: ChatActionButton):
        """Resets the state of a media rendering action button on failure."""
        button.label = "👁️ Photo"
        button.disabled = False