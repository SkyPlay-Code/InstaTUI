# archiver_view.py
import os
import time
import random
import requests
from textual.widgets import OptionList, Label, Button, Input, RichLog
from textual.containers import Vertical, Horizontal
from textual import work

class ArchiverView(Vertical):
    def compose(self):
        yield Label("📥 Chat Archiver", id="archiver-header")
        yield OptionList(id="dl-thread-list")
        with Horizontal(classes="action-row"):
            yield Input(placeholder="Messages to dl (leave blank for ALL)", id="dl-limit-input")
            yield Button("Start Download", id="start-dl-btn", variant="success", disabled=True)
        yield RichLog(id="dl-log", wrap=True, highlight=True, markup=True)

    def on_mount(self):
        self.loaded_threads = []
        self.selected_thread = None
        self.load_threads()

    @work(thread=True)
    def load_threads(self):
        cl = self.app.ig_client
        log = self.query_one("#dl-log")
        try:
            threads = cl.direct_threads(amount=30)
            self.app.call_from_thread(self.populate_threads, threads)
        except Exception as e:
            self.app.call_from_thread(log.write, f"[bold red]❌ Error: {e}[/bold red]")

    def populate_threads(self, threads):
        self.loaded_threads = threads
        opt_list = self.query_one("#dl-thread-list", OptionList)
        opt_list.clear_options()
        for t in threads:
            title = getattr(t, 'thread_title', None) or ", ".join([u.username for u in t.users])
            opt_list.add_option(f"💬 {title}")

    def get_media_url(self, msg):
        url, is_video = None, False
        if getattr(msg, 'media', None):
            if getattr(msg.media, 'video_url', None): url, is_video = msg.media.video_url, True
            elif getattr(msg.media, 'audio_url', None): url, is_video = msg.media.audio_url, False 
            elif getattr(msg.media, 'thumbnail_url', None): url, is_video = msg.media.thumbnail_url, False
        elif getattr(msg, 'visual_media', None) and getattr(msg.visual_media, 'media', None):
            vm = msg.visual_media.media
            if getattr(vm, 'video_versions', None): url, is_video = vm.video_versions[0].url, True
            elif getattr(vm, 'image_versions2', None) and vm.image_versions2.candidates:
                url, is_video = vm.image_versions2.candidates[0].url, False
        elif getattr(msg, 'clip', None) and getattr(msg.clip, 'video_url', None):
            url, is_video = msg.clip.video_url, True
        elif getattr(msg, 'xma_share', None):
            url = getattr(msg.xma_share, 'video_url', None) or getattr(msg.xma_share, 'preview_url', None)
        return str(url) if url else None, is_video

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.selected_thread = self.loaded_threads[event.option_index]
        self.query_one("#start-dl-btn").disabled = False

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-dl-btn":
            limit_val = self.query_one("#dl-limit-input").value
            limit = int(limit_val) if limit_val.isdigit() else 0
            self.download_chat(self.selected_thread, limit)

    @work(thread=True)
    def download_chat(self, thread, limit):
        cl = self.app.ig_client
        log = self.query_one("#dl-log")
        title = getattr(thread, 'thread_title', None) or ", ".join([u.username for u in thread.users])
        safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '_')]).rstrip()
        folder_name = os.path.join(os.getcwd(), "downloads", safe_title)
        os.makedirs(folder_name, exist_ok=True)
        
        try:
            fetch_amount = limit if limit > 0 else 0
            self.app.call_from_thread(log.write, f"📡 Archiving {safe_title}...")
            messages = cl.direct_messages(thread.id, amount=fetch_amount)
            messages.reverse()
            
            txt_path = os.path.join(folder_name, f"chat_log.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(f"--- Chat Archive: {title} ---\n\n")
                count = 0
                for msg in messages:
                    count += 1
                    time_str = msg.timestamp.astimezone().strftime("%Y-%m-%d %H:%M") if getattr(msg, 'timestamp', None) else "Unknown"
                    sender = "ME" if str(msg.user_id) == str(cl.user_id) else "THEM"
                    
                    if msg.item_type == "text":
                        f.write(f"[{time_str}] {sender}: {msg.text}\n")
                    else:
                        url, is_video = self.get_media_url(msg)
                        if url:
                            ext = ".m4a" if msg.item_type == "voice_media" else (".mp4" if is_video else ".jpg")
                            filename = f"media_{msg.id}{ext}"
                            filepath = os.path.join(folder_name, filename)
                            self.app.call_from_thread(log.write, f"  ↳ Downloading: {filename}")
                            try:
                                r = requests.get(url, stream=True, timeout=10)
                                if r.status_code == 200:
                                    with open(filepath, 'wb') as df:
                                        for chunk in r.iter_content(2048): df.write(chunk)
                                    f.write(f"[{time_str}] {sender}: <Local Media: {filename}>\n")
                            except: pass
                    if count % 15 == 0: time.sleep(random.uniform(1.0, 3.5))
            self.app.call_from_thread(log.write, f"[bold green]✅ ARCHIVE COMPLETE![/bold green] Total: {count} entries.")
        except Exception as e:
            self.app.call_from_thread(log.write, f"[bold red]❌ Pipeline Error: {e}[/bold red]")