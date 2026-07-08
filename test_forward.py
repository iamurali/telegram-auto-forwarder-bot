"""Local test runner for styled header forwarding.

Usage:
  cp .env.example .env   # fill in credentials and test IDs
  python test_forward.py --dry-run
  python test_forward.py
  python test_forward.py --force
"""
import argparse
import json
import os
import sys

from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPoll

from forward import (
    _fernet,
    _lookup_last_id,
    _set_last_id,
    build_header,
    format_message,
    load_dotenv_file,
    send_forward,
)

TEST_STATE_FILE = 'test_state.enc'


def load_test_config() -> dict:
    source_chat_id = int(os.environ.get('TEST_SOURCE_CHAT_ID', 0))
    recipient_id = int(os.environ.get('TEST_RECIPIENT_ID', 0))

    missing = []
    if not source_chat_id:
        missing.append('TEST_SOURCE_CHAT_ID')
    if not recipient_id:
        missing.append('TEST_RECIPIENT_ID')
    if missing:
        print(f"Error: set {', '.join(missing)} in .env")
        sys.exit(1)

    return {
        'source_chat_id': source_chat_id,
        'recipient_id': recipient_id,
        'route_name': os.environ.get('TEST_ROUTE_NAME', 'test-channel'),
        'header_label': os.environ.get('TEST_HEADER_LABEL', 'Test Channel'),
    }


def test_route(config: dict) -> dict:
    return {
        'name': config['route_name'],
        'header_label': config['header_label'],
        'source_chat_id': config['source_chat_id'],
        'recipients': [config['recipient_id']],
        'header': True,
    }


def load_test_state(api_hash: str) -> dict:
    if not os.path.exists(TEST_STATE_FILE):
        return {}
    with open(TEST_STATE_FILE, 'r') as f:
        token = f.read().strip()
    try:
        payload = _fernet(api_hash).decrypt(token.encode())
        state = json.loads(payload)
        if not isinstance(state, dict):
            raise ValueError(f"{TEST_STATE_FILE} must decrypt to a JSON object")
        return state
    except Exception as e:
        raise ValueError(f"Cannot load {TEST_STATE_FILE}: {e}") from e


def save_test_state(state: dict, source_chat_id: int, api_hash: str) -> None:
    out = {str(source_chat_id): _lookup_last_id(state, source_chat_id)}
    token = _fernet(api_hash).encrypt(json.dumps(out).encode()).decode()
    with open(TEST_STATE_FILE, 'w') as f:
        f.write(token + '\n')


def preview_message(msg, header: str) -> None:
    formatted = format_message(header, msg)
    print(f"  Message ID: {msg.id}")
    print(f"  Media: {'yes' if msg.media else 'no'}")
    print("  Preview:")
    for line in formatted.splitlines():
        print(f"    {line}")


def run(dry_run: bool, force: bool) -> None:
    load_dotenv_file()
    api_id = int(os.environ.get('API_ID', 0))
    api_hash = os.environ.get('API_HASH', '')
    session_string = os.environ.get('SESSION_STRING', '')

    if not api_id or not api_hash or not session_string:
        print("Error: set API_ID, API_HASH, and SESSION_STRING in .env")
        sys.exit(1)

    config = load_test_config()
    route = test_route(config)
    source_chat_id = config['source_chat_id']
    recipient_id = config['recipient_id']

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()

    try:
        state = load_test_state(api_hash)
        last_id = _lookup_last_id(state, source_chat_id)

        messages = client.get_messages(source_chat_id, limit=1)
        if not messages:
            print("No messages found in source channel")
            return

        msg = messages[0]

        if isinstance(msg.media, MessageMediaPoll):
            print(f"Latest message {msg.id} is a poll — skipped")
            return

        if not force and msg.id <= last_id:
            print(f"No new message (latest id={msg.id}, last forwarded id={last_id})")
            print("Use --force to re-send the latest message")
            return

        try:
            source_entity = client.get_entity(source_chat_id)
        except Exception:
            source_entity = None
        header = build_header(route, source_entity)

        print(f"--- Test route: {route['name']} ---")
        print(f"Source: {source_chat_id} -> Recipient: {recipient_id}")

        if dry_run:
            print("Dry run — not sending")
            preview_message(msg, header)
            return

        send_forward(client, recipient_id, msg, header)
        _set_last_id(state, source_chat_id, msg.id)
        save_test_state(state, source_chat_id, api_hash)
        print(f"Forwarded message {msg.id} to {recipient_id}")
    finally:
        client.disconnect()


def main():
    parser = argparse.ArgumentParser(description='Test styled header forwarding locally')
    parser.add_argument('--dry-run', action='store_true', help='Preview header + content without sending')
    parser.add_argument('--force', action='store_true', help='Re-send latest message even if already forwarded')
    args = parser.parse_args()
    run(dry_run=args.dry_run, force=args.force)


if __name__ == '__main__':
    main()
