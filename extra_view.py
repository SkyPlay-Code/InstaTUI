# extra_view.py
from textual.containers import Vertical
from textual.widgets import TabbedContent, TabPane

# Import the sub-views
from archiver_view import ArchiverView
from ghost_view import GhostView

class ExtraView(Vertical):
    """Holds both the Chat Archiver and the Ghost Viewer inside nested tabs."""

    def compose(self):
        with TabbedContent(initial="archiver-tab"):
            with TabPane("📥 Chat Archiver", id="archiver-tab"):
                yield ArchiverView()
            with TabPane("👻 Ghost Viewer", id="ghost-tab"):
                yield GhostView()
