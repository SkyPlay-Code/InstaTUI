
# account_view.py
from textual.widgets import LoadingIndicator, Label, Button
from textual.containers import VerticalScroll, Horizontal, Vertical
from textual import work

class AccountView(VerticalScroll):
    """Fetches and manages your private account data."""

    def compose(self):
        with Vertical(id="account-container"):
            yield Label("⚙️ My Account Settings", id="account-header")
            yield LoadingIndicator(id="account-loading")
            
            with Vertical(id="account-card"):
                yield Label("", id="acc-username", classes="acc-title")
                yield Label("", id="acc-fullname")
                yield Label("", id="acc-bio")
                
                # Private Information Box
                with Vertical(classes="acc-section"):
                    yield Label("🔒 PRIVATE INFORMATION", classes="acc-section-title")
                    yield Label("", id="acc-email")
                    yield Label("", id="acc-phone")
                    yield Label("", id="acc-birthday")
                    yield Label("", id="acc-gender")
                
                # Account Status Box
                with Vertical(classes="acc-section"):
                    yield Label("📊 ACCOUNT STATUS", classes="acc-section-title")
                    yield Label("", id="acc-private-status")
                    yield Label("", id="acc-business-status")
                
                # Action Buttons
                with Horizontal(id="account-actions"):
                    yield Button("🔄 Refresh Data", id="btn-acc-refresh", variant="primary")
                    yield Button("🔒 Set Account Private", id="btn-set-private", variant="error")
                    yield Button("🔓 Set Account Public", id="btn-set-public", variant="success")

    def on_mount(self):
        self.query_one("#account-card").display = False
        self.fetch_my_account()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-acc-refresh":
            self.query_one("#account-card").display = False
            self.query_one("#account-loading").display = True
            self.fetch_my_account()
        elif event.button.id == "btn-set-private":
            self.app.notify("Setting account to Private...")
            self.change_account_privacy(private=True)
        elif event.button.id == "btn-set-public":
            self.app.notify("Setting account to Public...")
            self.change_account_privacy(private=False)

    @work(thread=True)
    def fetch_my_account(self):
        try:
            # Fetches the deep, private 'Account' object
            account_data = self.app.ig_client.account_info()
            self.app.call_from_thread(self.display_account, account_data)
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Failed to load account: {e}", severity="error")

    @work(thread=True)
    def change_account_privacy(self, private: bool):
        try:
            cl = self.app.ig_client
            if private:
                success = cl.account_set_private()
            else:
                success = cl.account_set_public()
                
            if success:
                self.app.call_from_thread(self.app.notify, "✅ Privacy updated successfully!")
                self.app.call_from_thread(self.fetch_my_account) # Refresh UI
            else:
                self.app.call_from_thread(self.app.notify, "Update failed.", severity="warning")
        except Exception as e:
            self.app.call_from_thread(self.app.notify, f"Error: {e}", severity="error")

    def display_account(self, acc):
        self.query_one("#account-loading").display = False
        
        # We use standard object getters based on the `Account` class
        self.query_one("#acc-username").update(f"👤 [b]@{getattr(acc, 'username', 'Unknown')}[/b]")
        self.query_one("#acc-fullname").update(f"📛 Name: {getattr(acc, 'full_name', '')}")
        self.query_one("#acc-bio").update(f"📝 Bio: {getattr(acc, 'biography', 'No bio')}")
        
        # Deep private data formatting
        email = getattr(acc, 'email', 'Not Linked')
        phone = getattr(acc, 'phone_number', 'Not Linked')
        bday = getattr(acc, 'birthday', 'Not provided')
        
        genders = {1: "Male", 2: "Female", 3: "Custom/Prefer not to say"}
        gender_code = getattr(acc, 'gender', 3)
        gender = genders.get(gender_code, "Unknown")
        
        self.query_one("#acc-email").update(f"📧 Email: [blue]{email}[/]")
        self.query_one("#acc-phone").update(f"📱 Phone: [blue]{phone}[/]")
        self.query_one("#acc-birthday").update(f"🎂 Birthday: {bday}")
        self.query_one("#acc-gender").update(f"🚻 Gender ID: {gender}")

        # Statuses
        is_priv = getattr(acc, 'is_private', False)
        priv_text = "[red]🔒 PRIVATE[/red]" if is_priv else "[green]🔓 PUBLIC[/green]"
        self.query_one("#acc-private-status").update(f"Account Privacy: {priv_text}")
        
        is_bus = getattr(acc, 'is_business', False)
        bus_text = "[blue]💼 Professional/Business[/blue]" if is_bus else "[yellow]🧑 Personal[/yellow]"
        self.query_one("#acc-business-status").update(f"Account Type: {bus_text}")

        # Control the buttons based on current status to prevent spam clicking
        self.query_one("#btn-set-private").disabled = is_priv
        self.query_one("#btn-set-public").disabled = not is_priv

        self.query_one("#account-card").display = True
