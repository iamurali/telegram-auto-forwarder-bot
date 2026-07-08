"""Telegram auto-forwarder: multiple source chats via ROUTES_JSON GitHub secret.

Config: ROUTES_JSON env var (JSON array of {name, source_chat_id, recipients}).
State: state.enc locally; GitHub Actions cache in CI.
"""
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPoll
from telethon.extensions import html
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib
import hmac
import html as html_lib
import json
import os

STATE_FILE = 'state.enc'
OLD_STATE_FILE = 'last_message_ids.json'
MAX_CAPTION_LEN = 1024


def load_dotenv_file():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _fernet(api_hash: str) -> Fernet:
    if not api_hash:
        raise ValueError("API_HASH is required to read/write state")
    key = base64.urlsafe_b64encode(hashlib.sha256(api_hash.encode()).digest())
    return Fernet(key)


def _lookup_last_id(state: dict, source_id: int) -> int:
    return int(state.get(str(source_id), 0))


def _set_last_id(state: dict, source_id: int, msg_id: int) -> None:
    state[str(source_id)] = msg_id


def _import_old_hashed_state(old: dict, routes, api_hash: str) -> dict:
    """One-time import from previous hashed-key JSON format."""
    state = {}
    for route in routes:
        source_id = route['source_chat_id']
        hashed = hmac.new(
            api_hash.encode(),
            str(source_id).encode(),
            hashlib.sha256,
        ).hexdigest()
        plain = str(source_id)
        if hashed in old:
            state[plain] = int(old[hashed])
        elif plain in old:
            state[plain] = int(old[plain])
    return state


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
            'header_label': route.get('header_label'),
            'header': route.get('header', True),
        })
    return parsed


def load_state(api_hash, routes):
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            token = f.read().strip()
        try:
            payload = _fernet(api_hash).decrypt(token.encode())
            state = json.loads(payload)
            if not isinstance(state, dict):
                raise ValueError(f"{STATE_FILE} must decrypt to a JSON object")
            return state
        except InvalidToken as e:
            raise ValueError("Cannot decrypt state.enc — check API_HASH secret") from e

    if os.path.exists(OLD_STATE_FILE):
        with open(OLD_STATE_FILE, 'r') as f:
            old = json.load(f)
        print("Migrating last_message_ids.json to encrypted state.enc")
        return _import_old_hashed_state(old, routes, api_hash)

    print("No previous messages tracked, starting fresh")
    return {}


def save_state(state, routes, api_hash):
    out = {
        str(route['source_chat_id']): _lookup_last_id(state, route['source_chat_id'])
        for route in routes
    }
    token = _fernet(api_hash).encrypt(json.dumps(out).encode()).decode()
    with open(STATE_FILE, 'w') as f:
        f.write(token + '\n')
    if os.path.exists(OLD_STATE_FILE):
        os.remove(OLD_STATE_FILE)


def build_header(route, chat_entity=None) -> str:
    label = route.get('header_label') or route['name']
    lines = [f"<b>📢 {html_lib.escape(label)}</b>"]
    title = getattr(chat_entity, 'title', None) if chat_entity else None
    if title and title != label:
        lines.append(f"<i>{html_lib.escape(title)}</i>")
    lines.append("────────────────")
    return "\n".join(lines)


def format_message(header: str, msg) -> str:
    body = msg.message or ''
    if body:
        body = html.unparse(body, msg.entities or [])
        return f"{header}\n\n{body}"
    return header


def send_forward(client, recipient, msg, header=None):
    if header is None:
        client.send_message(recipient, msg)
        return

    formatted = format_message(header, msg)
    if msg.media:
        if len(formatted) > MAX_CAPTION_LEN:
            formatted = formatted[:MAX_CAPTION_LEN - 3] + '...'
        client.send_file(recipient, msg.media, caption=formatted, parse_mode='html')
    else:
        client.send_message(recipient, formatted, parse_mode='html', link_preview=True)


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

    header = None
    if route.get('header', True):
        try:
            source_entity = client.get_entity(source_chat)
        except Exception:
            source_entity = None
        header = build_header(route, source_entity)

    for msg in reversed(new_messages):
        try:
            if isinstance(msg.media, MessageMediaPoll):
                print(f"⊘ Skipped poll message {msg.id}")
                continue

            if msg.text or msg.media:
                for recipient in recipients:
                    try:
                        send_forward(client, recipient, msg, header)
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

    state = load_state(api_hash, routes)

    for route in routes:
        source_id = route['source_chat_id']
        last_id = _lookup_last_id(state, source_id)
        try:
            new_id = forward_route(client, route, last_id)
            if new_id is not None:
                _set_last_id(state, source_id, new_id)
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
    load_dotenv_file()
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
