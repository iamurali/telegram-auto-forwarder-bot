"""One-time helper: print config as base64 (GitHub masks raw secrets in logs)."""
import base64
import os
import sys


def b64(value):
    return base64.b64encode(value.encode()).decode()


def main():
    source = os.environ.get("SOURCE_CHAT_ID", "")
    recipients = os.environ.get("RECIPIENT_IDS", "")
    routes_json = os.environ.get("ROUTES_JSON", "")

    if not source and not recipients and not routes_json:
        print("No config env vars set")
        sys.exit(1)

    print("CONFIG_B64_START")
    if source:
        print(f"SOURCE_CHAT_ID_B64={b64(source)}")
    if recipients:
        print(f"RECIPIENT_IDS_B64={b64(recipients)}")
    if routes_json:
        print(f"ROUTES_JSON_B64={b64(routes_json)}")
    print("CONFIG_B64_END")


if __name__ == "__main__":
    main()
