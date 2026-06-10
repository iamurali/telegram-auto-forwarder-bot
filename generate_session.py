from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os


def generate_session(api_id: int, api_hash: str) -> str:
    client = TelegramClient(StringSession(), api_id, api_hash)
    client.start()
    session_string = client.session.save()
    client.disconnect()
    return session_string


if __name__ == "__main__":
    api_id = int(os.environ.get("API_ID", 0))
    api_hash = os.environ.get("API_HASH", "")

    if not api_id or not api_hash:
        print("Enter your Telegram API credentials from https://my.telegram.org")
        api_id = int(input("API ID: ").strip())
        api_hash = input("API Hash: ").strip()

    print("\nLog in with your Telegram account when prompted.\n")
    session_string = generate_session(api_id, api_hash)

    print("\n" + "=" * 60)
    print("YOUR SESSION STRING (COPY THIS!):")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    print("\nSave this as the SESSION_STRING GitHub Secret.")
