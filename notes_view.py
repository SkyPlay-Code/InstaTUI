# notes_view.py
import subprocess
from textual.widgets import OptionList, LoadingIndicator, Label, Button, Input
from textual.containers import Vertical, Horizontal
from textual import work

class NotesView(Vertical):
    """View, Play, and Post Instagram Notes via RAW API."""

    def compose(self):
        with Vertical(id="notes-container"):
            yield Label("📝 The Notes Board", id="notes-header", classes="section-header")
            
            with Horizontal(classes="action-row"):
                yield Input(placeholder="Share a thought (Max 60 chars)...", id="note-input")
                yield Button("Post Text", id="post-note-btn", variant="success")
                yield Button("🎵 Post +Music", id="browse-music-btn", variant="primary")
                
            with Vertical(id="music-container"):
                yield Label("🎵 Search or Browse Music", id="music-header")
                yield Input(placeholder="🔍 Search a song and hit Enter (Leave blank for Trending)", id="music-search")
                yield OptionList(id="music-list")
                with Horizontal(classes="action-row"):
                    yield Button("Confirm & Post", id="confirm-music-btn", variant="success")
                    yield Button("Cancel", id="cancel-music-btn", variant="error")

            with Horizontal(classes="action-row", id="notes-controls"):
                yield Button("🔄 Refresh Board", id="refresh-notes-btn", variant="primary")
                yield Button("▶️ Play Selected Audio", id="play-audio-btn", variant="success")
                yield Button("🗑️ Delete My Note", id="delete-note-btn", variant="error")
                
            yield LoadingIndicator(id="notes-loading")
            yield OptionList(id="notes-list")

    def on_mount(self):
        self.notes_cache = [] # Now holds RAW dictionaries, not stripped objects!
        self.music_cache = []
        self.alacorn_session_id = None
        
        self.query_one("#music-container").display = False
        self.query_one("#notes-loading").display = False
        self.fetch_notes_raw()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "music-search":
            query = event.input.value.strip()
            self.query_one("#music-list", OptionList).clear_options()
            if query:
                self.query_one("#music-header", Label).update(f"🎵 Searching Global DB for: '{query}'...")
                self.fetch_searched_music_raw(query)
            else:
                self.query_one("#music-header", Label).update("🎵 Fetching Global Trending Tracks...")
                self.fetch_trending_music()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-notes-btn":
            self.query_one("#notes-loading").display = True
            self.query_one("#notes-list").display = False
            self.fetch_notes_raw()
            
        elif event.button.id == "post-note-btn":
            text = self.query_one("#note-input").value.strip()
            self.query_one("#post-note-btn").disabled = True
            self.post_new_note(text)
            
        elif event.button.id == "delete-note-btn":
            self.delete_my_note()
            
        elif event.button.id == "browse-music-btn":
            self.query_one("#music-container").display = True
            self.query_one("#notes-list").display = False
            self.query_one("#notes-controls").display = False
            self.fetch_trending_music() 
            
        elif event.button.id == "cancel-music-btn":
            self.query_one("#music-container").display = False
            self.query_one("#notes-list").display = True
            self.query_one("#notes-controls").display = True
            
        elif event.button.id == "confirm-music-btn":
            text = self.query_one("#note-input").value.strip()
            music_list = self.query_one("#music-list", OptionList)
            if music_list.highlighted is not None and self.music_cache:
                selected_track = self.music_cache[music_list.highlighted]
                self.query_one("#confirm-music-btn").disabled = True
                self.post_music_note(text, selected_track)
                
        elif event.button.id == "play-audio-btn":
            list_ui = self.query_one("#notes-list", OptionList)
            if list_ui.highlighted is not None and self.notes_cache:
                # Cache contains raw dicts now!
                selected_note = self.notes_cache[list_ui.highlighted]
                m_data = self.find_music_in_note(selected_note)
                
                if m_data and (m_data.get('progressive_download_url') or m_data.get('fast_start_progressive_download_url')):
                    url = m_data.get('progressive_download_url') or m_data.get('fast_start_progressive_download_url')
                    self.play_note_audio(url, m_data.get('title', 'Track'))
                else:
                    self.app.notify("This note doesn't have playable music attached.", severity="warning")

    # ==========================
    # DATA PARSERS & HELPERS
    # ==========================

    def find_music_in_note(self, obj):
        if isinstance(obj, dict):
            if "progressive_download_url" in obj and "title" in obj:
                return obj
            for k, v in obj.items():
                res = self.find_music_in_note(v)
                if res: return res
        elif isinstance(obj, list):
            for i in obj:
                res = self.find_music_in_note(i)
                if res: return res
        return None

    @work(thread=True)
    def play_note_audio(self, url, title):
        try:
            self.app.call_from_thread(self.app.notify, f"🎧 Playing: {title}", timeout=4)
            with self.app.suspend():
                print("\033[2J\033[H", end="") 
                print(f"🎵 LISTENING TO INSTAGRAM NOTE: {title}")
                print("Press 'q' at any time to stop the track.")
                print("-" * 50)
                subprocess.run(["mpv", "--quiet", str(url)])
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Audio Error: {e}", severity="error")

    # ==========================
    # WORKER THREADS (API CALLS)
    # ==========================

    @work(thread=True)
    def fetch_notes_raw(self):
        """Bypasses instagrapi's Note wrapper so Music data isn't deleted!"""
        cl = self.app.ig_client
        try:
            # We hit the endpoint directly and take the raw JSON dicts
            res = cl.private_request("notes/get_notes/")
            raw_items = res.get("items", [])
            self.app.call_from_thread(self.display_notes, raw_items)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error fetching notes: {e}", severity="error")

    @work(thread=True)
    def fetch_trending_music(self):
        cl = self.app.ig_client
        try:
            music_data = cl.notes_music_browser()
            self.alacorn_session_id = music_data.get("alacorn_session_id")
            
            extracted = []
            for item in music_data.get("items", []):
                previews = item.get("playlist", {}).get("preview_items", [])
                for p in previews:
                    if p.get("track"): extracted.append(p.get("track"))
                    
            self.app.call_from_thread(self.update_music_ui, extracted, "🎵 Trending Audio")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Music Error: {e}", severity="error")

    
    @work(thread=True)
    def fetch_searched_music_raw(self, query):
        """Bypasses instagrapi's broken search wrapper and uses GET params!"""
        cl = self.app.ig_client
        try:
            # We must use `params` to force a GET request, avoiding the 405 error!
            payload = {
                "query": query,
                "browse_session_id": cl.generate_uuid()
            }
            res = cl.private_request("music/audio_global_search/", params=payload)
            
            # Safely dig out the tracks (Fixing the NoneType bug in the wrapper)
            extracted = []
            for item in res.get("items", []):
                track = item.get("track")
                if track: 
                    extracted.append(track)
                
            self.app.call_from_thread(self.update_music_ui, extracted, f"🎵 Search Results for '{query}'")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Search Error: {e}", severity="error")
            
    def update_music_ui(self, tracks, title):
        self.music_cache = tracks
        music_list = self.query_one("#music-list", OptionList)
        music_list.clear_options()
        
        for t in tracks:
            m_title = t.get('title', 'Unknown')
            artist = t.get('display_artist', 'Unknown')
            music_list.add_option(f"🎧 {m_title} - {artist}")
            
        self.query_one("#music-header", Label).update(f"{title} ({len(tracks)} found)")

    @work(thread=True)
    def post_new_note(self, text):
        cl = self.app.ig_client
        try:
            cl.create_note(text, audience=0)
            self.app.call_from_thread(self.app.notify, "✅ Note Posted Successfully!")
            self.app.call_from_thread(self.query_one("#note-input").__setattr__, "value", "")
            self.fetch_notes_raw()
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Post Error: {e}", severity="error")
        finally:
            self.app.call_from_thread(self.query_one("#post-note-btn").__setattr__, "disabled", False)

    @work(thread=True)
    def post_music_note(self, text, track):
        cl = self.app.ig_client
        try:
            cl.create_music_note(track=track, text=text, audience=0, alacorn_session_id=self.alacorn_session_id)
            self.app.call_from_thread(self.app.notify, "✅ Music Note Posted!")
            self.app.call_from_thread(self.query_one("#note-input").__setattr__, "value", "")
            self.app.call_from_thread(self.query_one("#cancel-music-btn").press)
            self.fetch_notes_raw()
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Music Post Error: {e}", severity="error")
        finally:
            self.app.call_from_thread(self.query_one("#confirm-music-btn").__setattr__, "disabled", False)

    @work(thread=True)
    def delete_my_note(self):
        cl = self.app.ig_client
        try:
            notes = cl.get_notes()
            my_note = cl.get_note_by_user(notes, cl.username_from_user_id(cl.user_id))
            if my_note:
                cl.delete_note(my_note.id)
                self.app.call_from_thread(self.app.notify, "✅ Note Deleted.")
                self.fetch_notes_raw()
            else:
                self.app.call_from_thread(self.app.notify, "No active Note to delete.", severity="warning")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Delete Error: {e}", severity="error")

    # ==========================
    # DISPLAY BOARD
    # ==========================

    def display_notes(self, raw_notes):
        self.notes_cache = raw_notes
        self.query_one("#notes-loading").display = False
        
        list_ui = self.query_one("#notes-list", OptionList)
        list_ui.clear_options()
        list_ui.display = True
        
        if not raw_notes:
            list_ui.add_option("Nobody has posted any Notes recently.")
            return

        my_uid = str(self.app.ig_client.user_id)

        for note_dict in raw_notes:
            user = note_dict.get('user', {})
            author_id = str(note_dict.get('user_id') or user.get('pk'))
            username = user.get('username', 'Unknown')
            
            if author_id == my_uid:
                prefix = "🌟 [bold green][YOU][/bold green]"
            else:
                prefix = f"👤 [bold]@{username}[/bold]"
                
            m_data = self.find_music_in_note(note_dict)
            text_str = note_dict.get('text', '') or ""
            
            if m_data:
                song_str = f" 🎧 [italic blue]{m_data.get('title')} - {m_data.get('display_artist')}[/italic blue]"
                # Handles edge case: Some people post ONLY a song with no text!
                display_string = f"{prefix}: {text_str}{song_str}" if text_str else f"{prefix}:{song_str}"
                list_ui.add_option(display_string)
            else:
                list_ui.add_option(f"{prefix}: {text_str}")
            
        self.query_one("#notes-header").update(f"📝 The Notes Board ({len(raw_notes)} active)")
