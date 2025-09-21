from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPoll
import os

def get_session(api_id, api_hash):
    client = TelegramClient('telegram_session', api_id, api_hash)
    client.start()
    # Get session string
    session_string = client.session.save()
    print("\n" + "="*60)
    print("YOUR SESSION STRING (COPY THIS!):")
    print("="*60)
    print(session_string)
    print("="*60)
    print("\nSave this for GitHub Secrets!")

def forward_message(api_id, api_hash, source_chat, recipients, session_string):
    # Connect to Telegram
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()
    
    # File to track last processed message
    last_msg_file = 'last_message_id.txt'
    
    # Get last processed message ID
    try:
        with open(last_msg_file, 'r') as f:
            last_msg_id = int(f.read().strip())
        print(f"Last processed message ID: {last_msg_id}")
    except FileNotFoundError:
        last_msg_id = 0
        print("No previous messages tracked, starting fresh")
    
    # Get new messages from source
    print(f"Checking for new messages in chat {source_chat}...")
    messages = client.get_messages(source_chat, limit=20)
    
    # Filter only new messages
    new_messages = [msg for msg in messages if msg.id > last_msg_id]
    
    if not new_messages:
        print("No new messages to forward")
    else:
        print(f"Found {len(new_messages)} new message(s)")
        print(f"Will forward to {len(recipients)} recipient(s)")
        
        # Forward messages in chronological order
        for msg in reversed(new_messages):
            try:
                # Skip polls
                if isinstance(msg.media, MessageMediaPoll):
                    print(f"⊘ Skipped poll message {msg.id}")
                    continue
                
                if msg.text or msg.media:
                    # Send to ALL recipients
                    for recipient in recipients:
                        try:
                            client.send_message(recipient, msg)
                            print(f"✓ Forwarded message {msg.id} to {recipient}")
                        except Exception as e:
                            print(f"✗ Failed to send to {recipient}: {e}")
                            
            except Exception as e:
                print(f"✗ Failed to process message {msg.id}: {e}")
        
        # Update last processed message ID
        with open(last_msg_file, 'w') as f:
            f.write(str(messages[0].id))
        print(f"Updated last message ID to: {messages[0].id}")
    
    client.disconnect()
    print("Done!")

if __name__ == "__main__":
    # Read from GitHub Secrets (environment variables)
    api_id_cred = int(os.environ.get('API_ID', 0))
    api_hash_cred = os.environ.get('API_HASH', '')
    session_string = os.environ.get('SESSION_STRING', '')
    source_chat = int(os.environ.get('SOURCE_CHAT_ID', 0))
    
    # Parse multiple recipients from comma-separated string
    # priya, ajay
    # 6339008344,1028364487
    recipients_str = os.environ.get('RECIPIENT_IDS', '')
    # recipients = [int(r.strip()) for r in recipients_str.split(',') if r.strip()]
    recipients = [6339008344,1028364487]
    
    print(f"Configuration:")
    print(f"  Source Chat: {source_chat}")
    print(f"  Recipients: {recipients}")
    
    # Uncomment below to get session string (run locally once)
    # get_session(api_id_cred, api_hash_cred)
    
    # Forward messages
    forward_message(api_id_cred, api_hash_cred, source_chat, recipients, session_string)
