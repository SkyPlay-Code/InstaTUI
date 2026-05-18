# inbox_screen.py
from textual.widgets import OptionList, LoadingIndicator, Label, Button
from textual.containers import Vertical
from textual import work

# Notice this is now a Vertical container, not a Screen!
class InboxView(Vertical):
    """The Component that displays your direct messages."""
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "refresh-inbox-btn":
            self.query_one("#chat-list").display = False
            self.query_one("#loading").display = True
            self.fetch_threads() # Instantly repulls newest texts!

    def compose(self):
        with Vertical(id="inbox-container"):
            yield Label("📫 Loading your Inbox...", id="inbox-header")
            yield LoadingIndicator(id="loading")
            yield Button("🔄 Refresh Inbox", id="refresh-inbox-btn")
            yield OptionList(id="chat-list")

    def on_mount(self):
        self.query_one("#chat-list").display = False
        self.loaded_threads = []
        self.fetch_threads()

    @work(thread=True)
    def fetch_threads(self):
        try:
            threads = self.app.ig_client.direct_threads(amount=15)
            self.app.call_from_thread(self.populate_inbox, threads)
        except Exception as e:
            self.app.call_from_thread(self.show_error, str(e))

    def populate_inbox(self, threads):
        self.loaded_threads = threads
        self.query_one("#loading").display = False
        
        chat_list = self.query_one("#chat-list", OptionList)
        chat_list.display = True
        
        for thread in threads:
            title = thread.thread_title
            if not title:
                title = ", ".join([user.username for user in thread.users])
            
            preview = "No messages"
            if thread.messages:
                last_msg = thread.messages[0]
                preview = last_msg.text if last_msg.text else f"[{last_msg.item_type}]"
                
            chat_list.add_option(f"[{title}] - {preview[:40]}...")
            
        self.query_one("#inbox-header", Label).update("📫 Your Inbox (Select a chat to open)")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        selected_thread = self.loaded_threads[event.option_index]
        from chat_screen import ChatScreen
        # We push the ChatScreen OVER the dashboard when a chat is clicked
        self.app.push_screen(ChatScreen(thread=selected_thread))

    def show_error(self, error_msg: str):
        self.query_one("#loading").display = False
        self.query_one("#inbox-header", Label).update(f"❌ Failed to load: {error_msg}")
