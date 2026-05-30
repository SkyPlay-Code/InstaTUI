# dashboard_screen.py
from textual.screen import Screen
from textual.widgets import TabbedContent, TabPane, Header, Footer

from inbox_screen import InboxView
from profile_view import ProfileView
from network_view import NetworkView
from reels_view import ReelsView
from account_view import AccountView
from extra_view import ExtraView 
from notes_view import NotesView  
from ghost_view import GhostView
from explore_view import ExploreView # <-- NEW IMPORT

class DashboardScreen(Screen):
    def compose(self):
        yield Header(show_clock=True)
        
        with TabbedContent(initial="inbox-tab"):
            with TabPane("📫 INBOX", id="inbox-tab"):
                yield InboxView()

            with TabPane("📝 NOTES", id="notes-tab"):
                yield NotesView()

            with TabPane("👻 GHOST", id="ghost-tab"):
                yield GhostView()
                
            # <-- DISCOVERY ENGINE TAB
            with TabPane("🌍 EXPLORE", id="explore-tab"):
                yield ExploreView()

            with TabPane("🕵️‍♂️ PROFILE", id="profile-tab"):
                yield ProfileView()
                
            with TabPane("🕸️ NETWORK", id="network-tab"):
                yield NetworkView() 
                
            with TabPane("🎬 REELS", id="reels-tab"):
                yield ReelsView() 
                
            with TabPane("⚙️ ACCOUNT", id="account-tab"):
                yield AccountView()
                
            with TabPane("🧰 EXTRA TOOLS", id="extra-tab"):
                yield ExtraView()
                        
        yield Footer()
