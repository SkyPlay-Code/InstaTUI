# account_view.py
import os
from pathlib import Path
from textual.widgets import LoadingIndicator, Label, Button, Input
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual import work

class AccountView(VerticalScroll):
    """Fetches, displays, and edits your private account data (Read & Edit Mode)."""

    def compose(self):
        with Vertical(id="account-container"):
            yield Label("⚙️ My Account Settings", id="account-header")
            yield LoadingIndicator(id="account-loading")
            
            # --- READ MODE (Profile Card) ---
            with Vertical(id="account-card"):
                yield Label("", id="acc-username", classes="acc-title")
                yield Label("", id="acc-fullname")
                yield Label("", id="acc-bio")
                
                with Vertical(classes="acc-section"):
                    yield Label("🔒 PRIVATE INFORMATION", classes="acc-section-title")
                    yield Label("", id="acc-email")
                    yield Label("", id="acc-phone")
                    yield Label("", id="acc-birthday")
                    yield Label("", id="acc-gender")
                
                with Vertical(classes="acc-section"):
                    yield Label("📊 ACCOUNT STATUS", classes="acc-section-title")
                    yield Label("", id="acc-private-status")
                    yield Label("", id="acc-business-status")
                
                with Horizontal(id="account-actions"):
                    yield Button("🔄 Refresh", id="btn-acc-refresh", variant="primary")
                    yield Button("✏️ Edit Profile", id="btn-acc-edit-toggle", variant="warning")

            # --- EDIT MODE (Form Fields) ---
            with Vertical(id="account-edit-form"):
                yield Label("✏️ Edit Profile Details", classes="acc-section-title")
                
                yield Label("Full Name:")
                yield Input(id="edit-fullname", placeholder="Your full name...")
                
                yield Label("Username:")
                yield Input(id="edit-username", placeholder="Your username...")
                
                yield Label("Biography:")
                yield Input(id="edit-bio", placeholder="Tell people about yourself...")
                
                yield Label("Email Address:")
                yield Input(id="edit-email", placeholder="Your email...")
                
                yield Label("Phone Number:")
                yield Input(id="edit-phone", placeholder="Your phone number...")
                
                yield Label("🖼️ New Profile Picture (Local File Path):")
                # Right-click pastes here too!
                yield Input(placeholder="C:\\path\\to\\image.jpg", id="edit-avatar-path")
                
                with Horizontal(id="edit-actions"):
                    yield Button("💾 Save Changes", id="btn-save-changes", variant="success")
                    yield Button("❌ Cancel", id="btn-cancel-edit", variant="error")

    def on_mount(self):
        self.query_one("#account-card").display = False
        self.query_one("#account-edit-form").display = False
        self.fetch_my_account()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-acc-refresh":
            self.query_one("#account-card").display = False
            self.query_one("#account-loading").display = True
            self.fetch_my_account()
            
        elif event.button.id == "btn-acc-edit-toggle":
            # Populate fields with current data and swap to Edit Mode!
            self.query_one("#account-card").display = False
            self.query_one("#account-edit-form").display = True
            
        elif event.button.id == "btn-cancel-edit":
            # Revert to Read Mode
            self.query_one("#account-edit-form").display = False
            self.query_one("#account-card").display = True
            
        elif event.button.id == "btn-save-changes":
            self.query_one("#btn-save-changes").disabled = True
            self.query_one("#account-loading").display = True
            self.save_profile_changes()

    @work(thread=True)
    def fetch_my_account(self):
        try:
            account_data = self.app.ig_client.account_info()
            self.app.call_from_thread(self.display_account, account_data)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Failed to load account: {e}", severity="error")

    def display_account(self, acc):
        self.query_one("#account-loading").display = False
        
        # Pull current values
        username = getattr(acc, 'username', '')
        fullname = getattr(acc, 'full_name', '')
        bio = getattr(acc, 'biography', '')
        email = getattr(acc, 'email', '')
        phone = getattr(acc, 'phone_number', '')
        bday = getattr(acc, 'birthday', 'Not provided')
        
        genders = {1: "Male", 2: "Female", 3: "Custom"}
        gender = genders.get(getattr(acc, 'gender', 3), "Unknown")

        # 1. Update Read Mode Card
        self.query_one("#acc-username").update(f"👤 [b]@{username}[/b]")
        self.query_one("#acc-fullname").update(f"Name: {fullname}")
        self.query_one("#acc-bio").update(f"Bio: {bio}")
        self.query_one("#acc-email").update(f"📧 Email: [blue]{email}[/]")
        self.query_one("#acc-phone").update(f"📱 Phone: [blue]{phone}[/]")
        self.query_one("#acc-birthday").update(f"🎂 Birthday: {bday}")
        self.query_one("#acc-gender").update(f"🚻 Gender: {gender}")

        is_priv = getattr(acc, 'is_private', False)
        priv_text = "[red]🔒 PRIVATE[/red]" if is_priv else "[green]🔓 PUBLIC[/green]"
        self.query_one("#acc-private-status").update(f"Privacy: {priv_text}")
        
        is_bus = getattr(acc, 'is_business', False)
        bus_text = "[blue]💼 Business[/blue]" if is_bus else "[yellow]🧑 Personal[/yellow]"
        self.query_one("#acc-business-status").update(f"Type: {bus_text}")

        # 2. Pre-populate Edit Mode Fields!
        self.query_one("#edit-fullname", Input).value = fullname
        self.query_one("#edit-username", Input).value = username
        self.query_one("#edit-bio", Input).value = bio
        self.query_one("#edit-email", Input).value = email
        self.query_one("#edit-phone", Input).value = phone
        self.query_one("#edit-avatar-path", Input).value = ""

        # Swap displays
        self.query_one("#account-edit-form").display = False
        self.query_one("#account-card").display = True

    @work(thread=True)
    def save_profile_changes(self):
        """Saves text changes and uploads new avatar natively from the background thread."""
        cl = self.app.ig_client
        
        # Grab values from the edit form
        new_fullname = self.query_one("#edit-fullname", Input).value.strip()
        new_username = self.query_one("#edit-username", Input).value.strip()
        new_bio = self.query_one("#edit-bio", Input).value.strip()
        new_email = self.query_one("#edit-email", Input).value.strip()
        new_phone = self.query_one("#edit-phone", Input).value.strip()
        avatar_path = self.query_one("#edit-avatar-path", Input).value.strip().strip('"').strip("'")

        try:
            # 1. Update Text Details using legacy accounts/edit_profile/
            self.app.call_from_thread(self.app.notify, "Saving profile text details...")
            cl.account_edit(
                username=new_username,
                full_name=new_fullname,
                biography=new_bio,
                phone_number=new_phone,
                email=new_email
            )
            
            # 2. Upload Avatar if path is specified using accounts/change_profile_picture/
            if avatar_path and os.path.exists(avatar_path):
                self.app.call_from_thread(self.app.notify, "Uploading new profile picture...")
                cl.account_change_picture(Path(avatar_path))
                
            self.app.call_from_thread(self.app.notify, "✅ Profile Updated Successfully!")
            
            # Re-fetch fresh account data and switch back to Read Mode
            account_data = cl.account_info()
            self.app.call_from_thread(self.display_account, account_data)
            
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Failed to save: {e}", severity="error")
            self.app.call_from_thread(self.revert_form_loading)

    def revert_form_loading(self):
        self.query_one("#account-loading").display = False
        self.query_one("#btn-save-changes").disabled = False