# Telegram Auto Forwarder Bot

Automatically forward messages from any Telegram chat to one or more recipients — powered by GitHub Actions. No server required.

## How It Works

1. GitHub Actions runs the forwarder on a schedule (every 6 hours)
2. The script connects to Telegram using your account session via [Telethon](https://github.com/LonamiWebs/Telethon)
3. It fetches the latest messages from each configured source chat
4. New messages (since the last run) are forwarded to that route's recipients
5. Per-source message IDs are committed back to the repo to track state

## Features

- Forward messages from multiple chats/channels/groups, each with its own recipients
- Supports text messages and media (photos, videos, documents, etc.)
- Skips unsupported message types (polls)
- Runs fully serverless via GitHub Actions
- State is persisted in `last_message_ids.json` — no external database needed

## Setup

### 1. Get Telegram API Credentials

1. Go to [my.telegram.org](https://my.telegram.org) and log in
2. Navigate to **API development tools**
3. Create a new application and copy your `API_ID` and `API_HASH`

### 2. Generate a Session String

Run locally:

```bash
pip install telethon
API_ID=your_api_id API_HASH=your_api_hash python generate_session.py
```

Log in with your phone number when prompted. Copy the printed session string — you'll need it as a secret.

Alternatively, uncomment `get_session()` in `forward.py` and run it once.

### 3. Get Chat and User IDs

Forward a message from the target chat to [@userinfobot](https://t.me/userinfobot) on Telegram to get numeric IDs.

> IDs for private channels/groups are usually negative numbers (e.g., `-1001234567890`).

### 4. Configure GitHub Secrets

In your repository go to **Settings > Secrets and variables > Actions** and add:

| Secret | Description |
|---|---|
| `API_ID` | Your Telegram API ID |
| `API_HASH` | Your Telegram API hash |
| `SESSION_STRING` | The session string generated in step 2 |
| `ROUTES_JSON` | JSON array of source-to-recipient routes (see below) |

#### `ROUTES_JSON` format

```json
[
  {
    "name": "news-channel",
    "source_chat_id": -1001234567890,
    "recipients": [111111111, 222222222]
  },
  {
    "name": "alerts",
    "source_chat_id": -1009876543210,
    "recipients": [333333333]
  }
]
```

| Field | Required | Description |
|---|---|---|
| `name` | No | Label for logs |
| `source_chat_id` | Yes | Numeric ID of the chat to forward from |
| `recipients` | Yes | Array of numeric recipient IDs |

#### Legacy single-route config

If `ROUTES_JSON` is not set, the forwarder falls back to these secrets:

| Secret | Description |
|---|---|
| `SOURCE_CHAT_ID` | Numeric ID of the chat to forward messages from |
| `RECIPIENT_IDS` | Comma-separated numeric IDs of recipients (e.g., `123456,789012`) |

### 5. Fork & Enable Actions

1. Fork this repository
2. Go to **Actions** tab and enable workflows
3. Trigger a manual run via **Actions > Forward Telegram Messages > Run workflow** to verify it works

## Migration from single-source setup

1. Create `ROUTES_JSON` from your existing secrets plus any new channels:

```json
[
  {
    "name": "existing-channel",
    "source_chat_id": YOUR_CURRENT_SOURCE_CHAT_ID,
    "recipients": [YOUR_RECIPIENT_1, YOUR_RECIPIENT_2]
  },
  {
    "name": "new-channel",
    "source_chat_id": NEW_SOURCE_CHAT_ID,
    "recipients": [NEW_RECIPIENT_1]
  }
]
```

2. Run the workflow manually and confirm both routes appear in the logs
3. Verify `last_message_ids.json` is committed with an entry per source
4. Remove `SOURCE_CHAT_ID` and `RECIPIENT_IDS` secrets once confirmed

On the first run, the script automatically migrates `last_message_id.txt` into `last_message_ids.json` for your existing source chat so no messages are re-forwarded.

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
├── generate_session.py         # One-time session string generator
├── last_message_ids.json       # Per-source last forwarded message IDs (auto-updated)
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
- The `last_message_ids.json` file is auto-committed by the workflow after each run to persist state.

## License

MIT
