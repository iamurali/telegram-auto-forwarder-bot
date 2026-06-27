"""Telegram auto-forwarder: multiple source chats via ROUTES_JSON GitHub secret.

Config: ROUTES_JSON env var (JSON array of {name, source_chat_id, recipients}).
State: last_message_ids.json (HMAC-hashed keys — channel IDs not stored in repo).
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPoll
import hashlib
import hmac
import json
import os

STATE_FILE = 'last_message_ids.json'


def _state_key(source_id: int, api_hash: str) -> str:
    """Opaque per-source key derived from API_HASH — channel ID not stored in repo."""
    if not api_hash:
        raise ValueError("API_HASH is required to read/write state")
    return hmac.new(
        api_hash.encode(),
        str(source_id).encode(),
        hashlib.sha256,
    ).hexdigest()


def _lookup_last_id(state: dict, source_id: int, api_hash: str) -> int:
    return int(state.get(_state_key(source_id, api_hash), 0))


def _set_last_id(state: dict, source_id: int, msg_id: int, api_hash: str) -> None:
    state[_state_key(source_id, api_hash)] = msg_id


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
    if not routes_json:
        raise ValueError("ROUTES_JSON is not set")

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


def load_state(api_hash):
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        if not isinstance(state, dict):
            raise ValueError(f"{STATE_FILE} must be a JSON object")
        return state
    except FileNotFoundError:
        print("No previous messages tracked, starting fresh")
        return {}


def save_state(state, routes, api_hash):
    """Persist state using HMAC-hashed keys only (no channel IDs in repo)."""
    out = {}
    for route in routes:
        source_id = route['source_chat_id']
        out[_state_key(source_id, api_hash)] = _lookup_last_id(state, source_id, api_hash)
    with open(STATE_FILE, 'w') as f:
        json.dump(out, f, indent=2)
        f.write('\n')


def forward_route(client, route, last_msg_id):
    source_chat = route['source_chat_id']
    recipients = route['recipients']
    name = route['name']

    print(f"\n--- Route: {name} ---")
    print(f"Last processed message ID: {last_msg_id}")

    try:
        messages = client.get_messages(source_chat, limit=20)
    except Exception as e:
        print(f"✗ Failed to fetch messages: {e}")
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
                        print(f"✓ Forwarded message {msg.id}")
                    except Exception as e:
                        print(f"✗ Failed to send message {msg.id}: {e}")
        except Exception as e:
            print(f"✗ Failed to process message {msg.id}: {e}")

    new_last_id = messages[0].id
    print(f"Updated last message ID to: {new_last_id}")
    return new_last_id


def forward_all(api_id, api_hash, routes, session_string):
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()

    state = load_state(api_hash)

    for route in routes:
        source_id = route['source_chat_id']
        last_id = _lookup_last_id(state, source_id, api_hash)
        try:
            new_id = forward_route(client, route, last_id)
            if new_id is not None:
                _set_last_id(state, source_id, new_id, api_hash)
        except Exception as e:
            print(f"✗ Route {route['name']} failed: {e}")

    save_state(state, routes, api_hash)
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
        print(f"  - {route['name']}: {len(route['recipients'])} recipient(s)")

    # Uncomment below to get session string (run locally once)
    # get_session(api_id_cred, api_hash_cred)
    # get_user_by_name(api_id_cred, api_hash_cred, session_string)
    forward_all(api_id_cred, api_hash_cred, routes, session_string)
