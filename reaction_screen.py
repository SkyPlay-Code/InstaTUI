# reaction_screen.py
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Button
from textual.containers import Vertical, Horizontal

class ReactionScreen(ModalScreen[str]):
    """A pop-up modal to capture custom emoji reactions."""

    BINDINGS = [("escape", "cancel", "Cancel")]

    QUICK_EMOJIS = ["❤️", "👍", "🔥", "😂", "😮", "😢"]

    def compose(self):
        with Vertical(id="reaction-box"):
            yield Label("😀 ENTER EMOJI TO REACT", id="reaction-title")
            
            # Use the loop index to create CSS-compliant IDs like "quick-0", "quick-1"
            with Horizontal(id="quick-reactions"):
                for idx, emoji in enumerate(self.QUICK_EMOJIS):
                    yield Button(emoji, id=f"quick-{idx}")

            yield Input(
                placeholder="Type or paste any emoji (e.g. 🔥, 😂, 👍)...", 
                id="reaction-input"
            )
            
            with Horizontal(classes="action-row", id="reaction-actions"):
                yield Button("React", id="submit-reaction-btn", variant="success")
                yield Button("Cancel", id="cancel-reaction-btn", variant="error")

    def on_mount(self) -> None:
        self.query_one("#reaction-input", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if not button_id:
            return

        if button_id == "submit-reaction-btn":
            self.submit()
        elif button_id == "cancel-reaction-btn":
            self.action_cancel()
        elif button_id.startswith("quick-"):
            try:
                # Extract the index to safely retrieve the correct emoji
                idx = int(button_id.replace("quick-", ""))
                emoji = self.QUICK_EMOJIS[idx]
                self.dismiss(emoji)
            except (ValueError, IndexError):
                pass

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.submit()

    def action_cancel(self) -> None:
        self.dismiss("")

    def submit(self) -> None:
        val = self.query_one("#reaction-input", Input).value.strip()
        if val:
            self.dismiss(val)