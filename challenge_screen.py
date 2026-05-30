
# challenge_screen.py
from textual.screen import ModalScreen
from textual.widgets import Input, Label, Button
from textual.containers import Vertical

class ChallengeScreen(ModalScreen[str]):
    """A pop-up modal to handle Instagram Security Checkpoints (2FA/Email/SMS)."""

    def compose(self):
        with Vertical(id="challenge-box"):
            yield Label("⚠️ SECURITY CHECKPOINT ⚠️", id="challenge-title")
            yield Label("Instagram requires verification. Check your SMS or Email for a 6-digit code.", id="challenge-desc")
            yield Input(placeholder="Enter security code...", id="challenge-input")
            yield Button("Unlock Account", id="submit-code-btn", variant="error")
            
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "submit-code-btn":
            self.submit()
            
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "challenge-input":
            self.submit()

    def submit(self):
        val = self.query_one("#challenge-input", Input).value.strip()
        if val:
            self.dismiss(val) # This sends the code back to main.py!
