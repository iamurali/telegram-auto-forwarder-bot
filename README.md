# LastPerson07 — Telegram Auto-Forwarder Bot

> Automatically forwards new messages from a source Telegram chat to one or more recipients, running on a schedule via GitHub Actions.

---

## ✨ Features

- **Modern terminal UI** powered by [Rich](https://github.com/Textualize/rich) — live progress bars, styled tables, and a branded banner
- **Multi-recipient** support via a comma-separated env variable
- **Retry logic** with exponential back-off on `FloodWait` and RPC errors
- **Poll skipping** — polls are automatically detected and skipped
- **Persistent message tracking** via `last_message_id.txt` committed back to the repo
- **Config validation** at startup with a clear status table
- **GitHub Actions** scheduled workflow (every 6 hours) with manual & webhook trigger support

---

## 🚀 Quick Setup

### 1. Fork / clone this repo

### 2. Get your Telegram API credentials
Go to [my.telegram.org](https://my.telegram.org) → API Development Tools → create an app.  
Save your **API ID** and **API Hash**.

### 3. Generate a session string (run locally once)
```bash
pip install -r requirements.txt
```
Uncomment this line in `forward.py`:
```python
# LastPerson07_get_session(api_id_cred, api_hash_cred)
```
Run:
```bash
API_ID=your_id API_HASH=your_hash python forward.py
```
Copy the printed session string.

### 4. Add GitHub Secrets
Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret Name      | Description                                      |
|------------------|--------------------------------------------------|
| `API_ID`         | Your Telegram API ID (number)                    |
| `API_HASH`       | Your Telegram API Hash                           |
| `SESSION_STRING` | The string generated in step 3                   |
| `SOURCE_CHAT_ID` | Chat/channel ID to forward messages **from**     |
| `RECIPIENT_IDS`  | Comma-separated user/chat IDs to forward **to**  |

### 5. Enable GitHub Actions
Push the code. The workflow runs every 6 hours automatically.  
You can also trigger it manually via **Actions → Run workflow**.

---

## 🛠 Project Structure

```
├── forward.py                        # Main bot script
├── requirements.txt                  # Python dependencies
├── last_message_id.txt               # Tracks last forwarded message ID
└── .github/
        └── forward.yml               # GitHub Actions workflow
```

---

## ⚙️ Configuration

All configuration is done via environment variables / GitHub Secrets.  
No hardcoded values — safe to commit.

---

## 📄 License

MIT — by **LastPerson07**
