# InstaTUI

InstaTUI is a terminal-based client for Instagram. It puts your dashboard directly into the command line, using Python's Textual framework and an embedded, modified version of the `instagrapi` API wrapper. 

It is designed for those who prefer working inside a terminal, want a lightweight distraction-free workspace, or need to run basic Instagram tasks on a headless system.

---

## Key Features

* **Inbox & Direct Messages:** Read and send messages, upload images (`/image <path>`), unsend messages, and play shared video or voice clips.
* **The Ghost Viewer:** Browse 24-hour stories and profile highlights anonymously without triggering seen receipts.
* **Notes Board:** View, search, and post text or music notes. You can also listen to posted notes audio natively.
* **Global Discovery:** Search for hashtags, recent posts, and users directly from the command line.
* **Network Explorer:** Analyze followers, following, mutual friends, and non-followers. Built-in safety limits help pace queries to protect your account.
* **Chat Archiver:** Save chat logs locally to plain text files, automatically downloading any associated media.
* **Profile Viewer:** Renders profile biographies, counters, and crops profile pictures into colored terminal ANSI block-art.
* **Notification Feed:** View your recent activity stream and toggle push notification settings.
* **Terminal Media Player:** Seamlessly suspends the TUI to play reels, audio, or high-definition pictures inside your terminal using `mpv`.

---

## Requirements

1. **Python 3.10+**
2. **mpv media player:** Installed on your system and added to your system's PATH variables (essential for video and image rendering).
3. **Optional (for HD media):** A terminal emulator that supports the Sixel or Kitty graphics protocols. If your terminal does not support this, media will fall back to retro character blocks (TCT mode).

---

## Setup & Installation

Clone the repository and install the required dependencies:

```bash
# Clone the repository
git clone https://github.com/yourusername/insta-tui.git
cd insta-tui

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate

# Install the dependencies
pip install textual requests pillow moviepy==2.2.1
```

*Note: Ensure `mpv` is installed on your operating system. For example:*
* **macOS:** `brew install mpv`
* **Ubuntu/Debian:** `sudo apt install mpv`
* **Windows:** Install via `choco install mpv` or download from the official site and add to your system Path.

---

## How to Use

Launch the application:

```bash
python main.py
```

### Authentication
* Enter your username and password on the login screen.
* If you have Two-Factor Authentication (2FA) enabled, a modal will prompt you to enter the SMS or Authenticator code.
* For security checkpoints (like "This was me" approvals), the TUI suspends and prompts you to verify on your phone before resuming.
* Successful logins generate a local `session.json` file to restore your session next time without asking for credentials.

### Navigation & Keybindings
* Use the left **Sidebar** to switch between different views (Inbox, Notes, Explore, Network, etc.).
* **`q`**: Quit the application.
* **`t`**: Toggle media quality instantly between Retro TCT (terminal blocks) and High-Definition Sixel/Kitty graphics.

---

## Security & Disclaimer

This project uses an unofficial API wrapper (`instagrapi`) that mimics mobile app requests. Automated clients always carry a risk of rate-limiting, temporary checkpoints, or account restriction if misused. 

* Use this tool cautiously and avoid aggressive scraping.
* Do not spam requests or run rapid network scans on accounts you do not own.
* Consider using a reliable proxy if you are running this on a remote server.
