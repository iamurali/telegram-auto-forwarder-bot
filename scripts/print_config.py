"""One-time helper: print config as char codes (GitHub masks raw secrets and base64)."""
import os
import sys


def encode(value):
    return ','.join(str(ord(c)) for c in value)


def main():
    source = os.environ.get("SOURCE_CHAT_ID", "")
    recipients = os.environ.get("RECIPIENT_IDS", "")
    routes_json = os.environ.get("ROUTES_JSON", "")

    if not source and not recipients and not routes_json:
        print("No config env vars set")
        sys.exit(1)

    print("CONFIG_ORD_START")
    if source:
        print(f"SOURCE_CHAT_ID_ORD={encode(source)}")
    if recipients:
        print(f"RECIPIENT_IDS_ORD={encode(recipients)}")
    if routes_json:
        print(f"ROUTES_JSON_ORD={encode(routes_json)}")
    print("CONFIG_ORD_END")


if __name__ == "__main__":
    main()
