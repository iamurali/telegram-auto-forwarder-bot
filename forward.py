"""Telegram auto-forwarder: multiple source chats via ROUTES_JSON GitHub secret.

Config: ROUTES_JSON env var (JSON array of {name, source_chat_id, recipients}).
State: last_message_ids.json (one last message ID per source).
Legacy: SOURCE_CHAT_ID + RECIPIENT_IDS env vars for a single route.
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPoll
import json
import os

STATE_FILE = 'last_message_ids.json'
LEGACY_STATE_FILE = 'last_message_id.txt'


def get_session(api_id, api_hash):
    client = TelegramClient('telegram_session', api_id, api_hash)
    client.start()
    session_string = client.session.save()
    print("\n" + "=" * 60)
    print("YOUR SESSION STRING (COPY THIS!):")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    print("\nSave this for GitHub Secrets!")


def load_routes():
    routes_json = os.environ.get('ROUTES_JSON', '').strip()
    if routes_json:
        try:
            routes = json.loads(routes_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid ROUTES_JSON: {e}") from e

        if not isinstance(routes, list) or not routes:
            raise ValueError("ROUTES_JSON must be a non-empty JSON array")

        seen_sources = set()
        parsed = []
        for i, route in enumerate(routes):
            if not isinstance(route, dict):
                raise ValueError(f"Route at index {i} must be an object")
            if 'source_chat_id' not in route:
                raise ValueError(f"Route at index {i} missing source_chat_id")
            if not route.get('recipients'):
                raise ValueError(f"Route at index {i} missing recipients")

            source_id = int(route['source_chat_id'])
            if source_id in seen_sources:
                raise ValueError(f"Duplicate source_chat_id: {source_id}")
            seen_sources.add(source_id)

            parsed.append({
                'name': route.get('name', str(source_id)),
                'source_chat_id': source_id,
                'recipients': [int(r) for r in route['recipients']],
            })
        return parsed

    source_chat = int(os.environ.get('SOURCE_CHAT_ID', 0))
    recipients_str = os.environ.get('RECIPIENT_IDS', '')
    recipients = [int(r.strip()) for r in recipients_str.split(',') if r.strip()]

    if not source_chat or not recipients:
        raise ValueError(
            "No routes configured. Set ROUTES_JSON or SOURCE_CHAT_ID + RECIPIENT_IDS"
        )

    return [{
        'name': str(source_chat),
        'source_chat_id': source_chat,
        'recipients': recipients,
    }]


def _migrate_legacy_state(routes):
    try:
        with open(LEGACY_STATE_FILE, 'r') as f:
            legacy_id = int(f.read().strip())
    except FileNotFoundError:
        return {}

    source_chat = int(os.environ.get('SOURCE_CHAT_ID', 0))
    if not source_chat and len(routes) == 1:
        source_chat = routes[0]['source_chat_id']

    if not source_chat:
        print("Legacy state file found but no SOURCE_CHAT_ID to migrate")
        return {}

    print(f"Migrated legacy state: {source_chat} -> {legacy_id}")
    return {str(source_chat): legacy_id}


def load_state(routes):
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        if not isinstance(state, dict):
            raise ValueError(f"{STATE_FILE} must be a JSON object")
        return state
    except FileNotFoundError:
        state = _migrate_legacy_state(routes)
        if not state:
            print("No previous messages tracked, starting fresh")
        return state


def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)
        f.write('\n')


def forward_route(client, route, last_msg_id):
    source_chat = route['source_chat_id']
    recipients = route['recipients']
    name = route['name']

    print(f"\n--- Route: {name} (source {source_chat}) ---")
    print(f"Last processed message ID: {last_msg_id}")

    try:
        messages = client.get_messages(source_chat, limit=20)
    except Exception as e:
        print(f"✗ Failed to fetch messages from {source_chat}: {e}")
        return None

    new_messages = [msg for msg in messages if msg.id > last_msg_id]

    if not new_messages:
        print("No new messages to forward")
        return None

    print(f"Found {len(new_messages)} new message(s)")
    print(f"Will forward to {len(recipients)} recipient(s)")

    for msg in reversed(new_messages):
        try:
            if isinstance(msg.media, MessageMediaPoll):
                print(f"⊘ Skipped poll message {msg.id}")
                continue

            if msg.text or msg.media:
                for recipient in recipients:
                    try:
                        client.send_message(recipient, msg)
                        print(f"✓ Forwarded message {msg.id} to {recipient}")
                    except Exception as e:
                        print(f"✗ Failed to send to {recipient}: {e}")
        except Exception as e:
            print(f"✗ Failed to process message {msg.id}: {e}")

    new_last_id = messages[0].id
    print(f"Updated last message ID to: {new_last_id}")
    return new_last_id


def forward_all(api_id, api_hash, routes, session_string):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()

    state = load_state(routes)

    for route in routes:
        source_id = route['source_chat_id']
        last_id = state.get(str(source_id), 0)
        try:
            new_id = forward_route(client, route, last_id)
            if new_id is not None:
                state[str(source_id)] = new_id
        except Exception as e:
            print(f"✗ Route {route['name']} failed: {e}")

    save_state(state)
    client.disconnect()
    print("\nDone!")


def get_user_by_name(api_id, api_hash, session_string):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()

    try:
        user = client.get_entity('username')  # replace with target @username
        print(f"Username: @{user.username}")
        print(f"User ID: {user.id}")
        print(f"Name: {user.first_name} {user.last_name or ''}")
    except Exception as e:
        print(f"Error: {e}")

    client.disconnect()


if __name__ == "__main__":
    api_id_cred = int(os.environ.get('API_ID', 0))
    api_hash_cred = os.environ.get('API_HASH', '')
    session_string = os.environ.get('SESSION_STRING', '')

    routes = load_routes()
    print(f"Configuration: {len(routes)} route(s)")
    for route in routes:
        print(
            f"  - {route['name']}: source {route['source_chat_id']} "
            f"-> {len(route['recipients'])} recipient(s)"
        )

    # Uncomment below to get session string (run locally once)
    # get_session(api_id_cred, api_hash_cred)
    # get_user_by_name(api_id_cred, api_hash_cred, session_string)
    forward_all(api_id_cred, api_hash_cred, routes, session_string)
