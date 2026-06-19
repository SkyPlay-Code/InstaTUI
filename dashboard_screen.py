# dashboard_screen.py
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import ContentSwitcher, Footer, Header, Label, ListItem, ListView

from account_view import AccountView
from explore_view import ExploreView
from extra_view import ExtraView

# Import our Views
from inbox_screen import InboxView
from network_view import NetworkView
from notes_view import NotesView
from profile_view import ProfileView
from reels_view import ReelsView


class DashboardScreen(Screen):
    """The Sidebar Dashboard layout."""

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            # Left Sidebar Navigation
            with Vertical(id="sidebar"):
                yield Label("🧭 NAVIGATION", id="sidebar-title")
                with ListView(id="nav-list"):
                    yield ListItem(Label("📫 Inbox"), id="nav-inbox")
                    yield ListItem(Label("📝 Notes"), id="nav-notes")
                    yield ListItem(Label("🌍 Explore"), id="nav-explore")
                    yield ListItem(Label("🕵️‍♂️ Profile"), id="nav-profile")
                    yield ListItem(Label("🕸️ Network"), id="nav-network")
                    yield ListItem(Label("🎬 Reels"), id="nav-reels")
                    yield ListItem(Label("⚙️ Account"), id="nav-account")
                    yield ListItem(Label("🧰 Extra Tools"), id="nav-extra")
            
            # Right Content Panel
            with ContentSwitcher(initial="inbox-view", id="content-area"):
                yield InboxView(id="inbox-view")
                yield NotesView(id="notes-view")
                yield ExploreView(id="explore-view")
                yield ProfileView(id="profile-view")
                yield NetworkView(id="network-view")
                yield ReelsView(id="reels-view")
                yield AccountView(id="account-view")
                yield ExtraView(id="extra-view") # Contains both Archiver and Ghost inside!
                    
        yield Footer()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Dynamically swaps the right content switcher based on sidebar clicks!"""
        switcher = self.query_one("#content-area", ContentSwitcher)
        
        nav_map = {
            "nav-inbox": "inbox-view",
            "nav-notes": "notes-view",
            "nav-explore": "explore-view",
            "nav-profile": "profile-view",
            "nav-network": "network-view",
            "nav-reels": "reels-view",
            "nav-account": "account-view",
            "nav-extra": "extra-view"
        }
        
        target_view = nav_map.get(event.item.id)  # pyright: ignore[reportArgumentType]
        if target_view:
            switcher.current = target_view