# Telegram Auto Forwarder Bot

Automatically forward messages from any Telegram chat to one or more recipients — powered by GitHub Actions. No server required.

## How It Works

1. GitHub Actions runs the forwarder on a schedule (every 6 hours)
2. The script connects to Telegram using your account session via [Telethon](https://github.com/LonamiWebs/Telethon)
3. It fetches the latest messages from the source chat
4. New messages (since the last run) are forwarded to all configured recipients
5. The last processed message ID is committed back to the repo to track state

## Features

- Forward messages from any chat/channel/group to multiple recipients
- Supports text messages and media (photos, videos, documents, etc.)
- Skips unsupported message types (polls)
- Runs fully serverless via GitHub Actions
- State is persisted in `last_message_id.txt` — no external database needed

## Setup

### 1. Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org) and log in
2. Navigate to **API development tools**
3. Create a new application and copy your `API_ID` and `API_HASH`

### 2. Generate a Session String

Run the script locally once to generate a session string:

```python
# In forward.py, uncomment this line under __main__:
get_session(api_id_cred, api_hash_cred)
```

```bash
pip install telethon
API_ID=your_api_id API_HASH=your_api_hash python forward.py
```

Log in with your phone number when prompted. Copy the printed session string — you'll need it as a secret.

### 3. Get Chat and User IDs

To find the `SOURCE_CHAT_ID` or numeric `RECIPIENT_IDS`, you can use the helper function in the script or forward a message from the target chat to [@userinfobot](https://t.me/userinfobot) on Telegram.

> IDs for private channels/groups are usually negative numbers (e.g., `-1001234567890`).

### 4. Configure GitHub Secrets

In your repository go to **Settings > Secrets and variables > Actions** and add:

| Secret | Description |
|---|---|
| `API_ID` | Your Telegram API ID |
| `API_HASH` | Your Telegram API hash |
| `SESSION_STRING` | The session string generated in step 2 |
| `SOURCE_CHAT_ID` | Numeric ID of the chat to forward messages from |
| `RECIPIENT_IDS` | Comma-separated numeric IDs of recipients (e.g., `123456,789012`) |

### 5. Fork & Enable Actions

1. Fork this repository
2. Go to **Actions** tab and enable workflows
3. Trigger a manual run via **Actions > Forward Telegram Messages > Run workflow** to verify it works

## Schedule

The workflow runs every **6 hours** by default. To change the frequency, edit the cron expression in `.github/workflows/forward.yml`:

```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
```

Use [crontab.guru](https://crontab.guru) to build your preferred schedule.

> **Note:** GitHub Actions has a minimum interval of ~5 minutes, and free-tier scheduled workflows may be delayed during high load.

## Manual Trigger

You can trigger the forwarder anytime from the **Actions** tab using the **Run workflow** button, or via the GitHub API:

```bash
curl -X POST \
  -H "Authorization: token YOUR_GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/YOUR_USERNAME/telegram-auto-forwarder-bot/dispatches \
  -d '{"event_type":"telegram-forward"}'
```

## Project Structure

```
.
├── forward.py                  # Core forwarding logic
├── last_message_id.txt         # Tracks the last forwarded message (auto-updated)
├── requirements.txt            # Python dependencies (telethon)
└── .github/
    └── workflows/
        └── forward.yml         # GitHub Actions workflow
```

## Dependencies

- [Telethon](https://github.com/LonamiWebs/Telethon) — MTProto-based Telegram client for Python

## Important Notes

- This bot acts as a **user account**, not a bot account. Use responsibly and in accordance with [Telegram's Terms of Service](https://core.telegram.org/api/terms).
- Keep your `SESSION_STRING` secret — it grants full access to your Telegram account.
- The `last_message_id.txt` file is auto-committed by the workflow after each run to persist state.

## License

MIT
