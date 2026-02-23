import os
import time
import sys
import logging
from datetime import datetime
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPoll
from telethon.errors import FloodWaitError, RPCError, SessionPasswordNeededError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.text import Text
from rich.rule import Rule
from rich.align import Align
from rich import box
from rich.live import Live
from rich.columns import Columns
from rich.style import Style
from rich.traceback import install as install_rich_traceback

# ── Rich Traceback ─────────────────────────────────────────────────────────────
install_rich_traceback()

# ── Console ────────────────────────────────────────────────────────────────────
console = Console()

# ── Constants ──────────────────────────────────────────────────────────────────
LAST_MSG_FILE    = "last_message_id.txt"
FETCH_LIMIT      = 20
RETRY_ATTEMPTS   = 3
RETRY_DELAY      = 2   # seconds
VERSION          = "2.0.0"
AUTHOR           = "LastPerson07"


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  BANNER
# ╚══════════════════════════════════════════════════════════════════════════════╝
def LastPerson07_print_banner() -> None:
    """Print the LastPerson07 branded ASCII banner."""
    banner = r"""
 ██╗      █████╗ ███████╗████████╗██████╗ ███████╗██████╗ ███████╗ ██████╗ ███╗   ██╗ ██████╗ ███████╗
 ██║     ██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔════╝██╔══██╗██╔════╝██╔═══██╗████╗  ██║██╔═████╗╚════██║
 ██║     ███████║███████╗   ██║   ██████╔╝█████╗  ██████╔╝███████╗██║   ██║██╔██╗ ██║██║██╔██║    ██╔╝
 ██║     ██╔══██║╚════██║   ██║   ██╔═══╝ ██╔══╝  ██╔══██╗╚════██║██║   ██║██║╚██╗██║████╔╝██║   ██╔╝ 
 ███████╗██║  ██║███████║   ██║   ██║     ███████╗██║  ██║███████║╚██████╔╝██║ ╚████║╚██████╔╝   ██║  
 ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝    ╚═╝  
    """
    console.print(Align.center(Text(banner, style="bold cyan")))
    console.print(Align.center(
        Text(f"  Telegram Auto-Forwarder Bot  •  v{VERSION}  •  by {AUTHOR}  ", style="bold white on blue")
    ))
    console.print(Align.center(
        Text(f"  {datetime.now().strftime('%A, %d %B %Y  |  %H:%M:%S')}  ", style="dim white")
    ))
    console.print()
    console.print(Rule(style="cyan"))
    console.print()


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  LOGGING
# ╚══════════════════════════════════════════════════════════════════════════════╝
def LastPerson07_setup_logging() -> logging.Logger:
    """Configure and return a logger with a clean format."""
    log = logging.getLogger(AUTHOR)
    log.setLevel(logging.DEBUG)
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-8s  %(message)s",
            datefmt="%H:%M:%S"
        ))
        log.addHandler(handler)
    return log

log = LastPerson07_setup_logging()


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  CONFIG VALIDATION
# ╚══════════════════════════════════════════════════════════════════════════════╝
def LastPerson07_validate_config(api_id: int, api_hash: str,
                                  session_string: str, source_chat: int,
                                  recipients: list) -> bool:
    """Validate all required config values and display a status table."""
    checks = {
        "API_ID"          : bool(api_id),
        "API_HASH"        : bool(api_hash),
        "SESSION_STRING"  : bool(session_string),
        "SOURCE_CHAT_ID"  : bool(source_chat),
        "RECIPIENT_IDS"   : bool(recipients),
    }

    table = Table(
        title="[bold cyan]⚙  Configuration Check[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
        title_justify="left"
    )
    table.add_column("Variable",  style="bold white",  min_width=20)
    table.add_column("Status",    justify="center",    min_width=10)
    table.add_column("Detail",    style="dim white")

    all_ok = True
    for key, ok in checks.items():
        if ok:
            table.add_row(key, "[bold green]  ✓  OK[/bold green]", "Set")
        else:
            table.add_row(key, "[bold red]  ✗  MISSING[/bold red]", "Not set / empty")
            all_ok = False

    console.print(table)
    console.print()

    if not all_ok:
        console.print(Panel(
            "[bold red]✗  One or more required environment variables are missing.\n"
            "   Please check your GitHub Secrets and try again.[/bold red]",
            border_style="red", title="[red]Configuration Error[/red]"
        ))
    return all_ok


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  FILE I/O
# ╚══════════════════════════════════════════════════════════════════════════════╝
def LastPerson07_load_last_id() -> int:
    """Load the last processed message ID from disk."""
    try:
        with open(LAST_MSG_FILE, "r") as f:
            msg_id = int(f.read().strip())
        console.print(f"  [dim]📂  Last tracked message ID:[/dim] [cyan]{msg_id}[/cyan]")
        return msg_id
    except FileNotFoundError:
        console.print("  [dim]📂  No previous message ID found — starting fresh.[/dim]")
        return 0
    except ValueError:
        console.print("  [yellow]⚠  Corrupted last_message_id.txt — resetting to 0.[/yellow]")
        return 0


def LastPerson07_save_last_id(msg_id: int) -> None:
    """Save the latest processed message ID to disk."""
    with open(LAST_MSG_FILE, "w") as f:
        f.write(str(msg_id))
    console.print(f"  [dim]💾  Saved last message ID:[/dim] [cyan]{msg_id}[/cyan]")


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  SEND WITH RETRY
# ╚══════════════════════════════════════════════════════════════════════════════╝
def LastPerson07_send_with_retry(client, recipient, msg,
                                  attempts: int = RETRY_ATTEMPTS) -> bool:
    """Send a message to a recipient with retry logic on transient failures."""
    for attempt in range(1, attempts + 1):
        try:
            client.send_message(recipient, msg)
            return True
        except FloodWaitError as e:
            console.print(f"    [yellow]⚠  Flood wait — sleeping {e.seconds}s "
                          f"(attempt {attempt}/{attempts})[/yellow]")
            time.sleep(e.seconds)
        except RPCError as e:
            console.print(f"    [red]✗  RPC error → {recipient}: {e} "
                          f"(attempt {attempt}/{attempts})[/red]")
            if attempt < attempts:
                time.sleep(RETRY_DELAY * attempt)
        except Exception as e:
            console.print(f"    [red]✗  Unexpected error → {recipient}: {e}[/red]")
            break
    return False


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  GET SESSION
# ╚══════════════════════════════════════════════════════════════════════════════╝
def LastPerson07_get_session(api_id: int, api_hash: str) -> None:
    """Authenticate interactively and display the session string for storage."""
    console.print(Panel(
        "[bold yellow]  Running in SESSION GENERATION mode.\n"
        "  Follow the prompts to log in to Telegram.[/bold yellow]",
        title="[yellow]🔑  Get Session String[/yellow]",
        border_style="yellow"
    ))
    client = TelegramClient("telegram_session", api_id, api_hash)
    client.start()
    session_string = client.session.save()
    client.disconnect()

    console.print()
    console.print(Panel(
        f"[bold green]{session_string}[/bold green]",
        title="[green]✓  YOUR SESSION STRING — COPY AND SAVE THIS![/green]",
        subtitle="[dim]Store in GitHub Secrets as SESSION_STRING[/dim]",
        border_style="green",
        padding=(1, 4)
    ))


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  GET USER BY NAME
# ╚══════════════════════════════════════════════════════════════════════════════╝
def LastPerson07_get_user_by_name(api_id: int, api_hash: str,
                                   session_string: str,
                                   username: str = "esper1297") -> None:
    """Look up a Telegram user by username and display their details."""
    console.print(Panel(
        f"[bold white]Looking up user:[/bold white] [cyan]@{username}[/cyan]",
        title="[cyan]👤  User Lookup[/cyan]",
        border_style="cyan"
    ))
    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    client.connect()
    try:
        user = client.get_entity(username)
        table = Table(box=box.SIMPLE_HEAVY, border_style="cyan", show_header=False)
        table.add_column("Field",  style="bold white", min_width=14)
        table.add_column("Value",  style="cyan")
        table.add_row("Username",  f"@{user.username}")
        table.add_row("User ID",   str(user.id))
        table.add_row("Full Name", f"{user.first_name} {user.last_name or ''}".strip())
        console.print(table)
    except Exception as e:
        console.print(f"  [red]✗  Error looking up '{username}': {e}[/red]")
    finally:
        client.disconnect()


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  FORWARD MESSAGES  (main logic)
# ╚══════════════════════════════════════════════════════════════════════════════╝
def LastPerson07_forward_messages(api_id: int, api_hash: str, source_chat: int,
                                   recipients: list, session_string: str) -> None:
    """Fetch new messages from source_chat and forward them to all recipients."""
    console.print(Panel(
        f"[bold white]Source Chat:[/bold white]  [cyan]{source_chat}[/cyan]\n"
        f"[bold white]Recipients :[/bold white]  [cyan]{len(recipients)} target(s)[/cyan]\n"
        f"[bold white]Fetch Limit:[/bold white]  [cyan]{FETCH_LIMIT} messages[/cyan]",
        title="[cyan]📡  Forward Session — LastPerson07[/cyan]",
        border_style="cyan"
    ))
    console.print()

    client = TelegramClient(StringSession(session_string), api_id, api_hash)

    with Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[cyan]{task.description}[/cyan]"),
        BarColumn(bar_width=30, style="cyan", complete_style="green"),
        TextColumn("[green]{task.completed}/{task.total}[/green]"),
        console=console,
        transient=False
    ) as progress:

        # ── Connect ──────────────────────────────────────────────────────────
        connect_task = progress.add_task("Connecting to Telegram...", total=1)
        client.connect()
        progress.update(connect_task, completed=1, description="[green]✓  Connected[/green]")

        try:
            # ── Load last ID ─────────────────────────────────────────────────
            last_msg_id = LastPerson07_load_last_id()

            # ── Fetch messages ───────────────────────────────────────────────
            fetch_task = progress.add_task("Fetching messages from source...", total=1)
            messages = client.get_messages(source_chat, limit=FETCH_LIMIT)
            progress.update(fetch_task, completed=1,
                            description=f"[green]✓  Fetched {len(messages)} message(s)[/green]")

            if not messages:
                console.print("  [yellow]⚠  No messages returned from source chat.[/yellow]")
                return

            # ── Filter new ───────────────────────────────────────────────────
            new_messages = [m for m in messages if m.id > last_msg_id]

            if not new_messages:
                console.print()
                console.print(Panel(
                    "[bold green]✓  No new messages to forward. All caught up![/bold green]",
                    border_style="green", padding=(0, 2)
                ))
                return

            console.print()
            console.print(f"  [bold green]●  {len(new_messages)} new message(s) found[/bold green] "
                          f"[dim]→ forwarding to {len(recipients)} recipient(s)[/dim]")
            console.print()

            # ── Forward ──────────────────────────────────────────────────────
            total_sends  = len(new_messages) * len(recipients)
            fwd_task     = progress.add_task("Forwarding messages...", total=total_sends)

            sent_count   = 0
            skip_count   = 0
            fail_count   = 0

            results_table = Table(
                title="[bold cyan]📨  Forward Log[/bold cyan]",
                box=box.ROUNDED, border_style="cyan",
                show_lines=True, title_justify="left"
            )
            results_table.add_column("Msg ID",     style="bold white",   justify="right",  min_width=10)
            results_table.add_column("Type",       style="dim white",                      min_width=10)
            results_table.add_column("Recipient",  style="cyan",                           min_width=16)
            results_table.add_column("Status",     justify="center",                       min_width=14)
            results_table.add_column("Time",       style="dim",           justify="right", min_width=10)

            for msg in reversed(new_messages):
                try:
                    # Detect type
                    if isinstance(msg.media, MessageMediaPoll):
                        results_table.add_row(
                            str(msg.id), "Poll", "—",
                            "[yellow]⊘  Skipped[/yellow]",
                            datetime.now().strftime("%H:%M:%S")
                        )
                        skip_count += 1
                        progress.advance(fwd_task, len(recipients))
                        continue

                    if not (msg.text or msg.media):
                        results_table.add_row(
                            str(msg.id), "Empty", "—",
                            "[yellow]⊘  Skipped[/yellow]",
                            datetime.now().strftime("%H:%M:%S")
                        )
                        skip_count += 1
                        progress.advance(fwd_task, len(recipients))
                        continue

                    msg_type = "📷 Media" if msg.media else "💬 Text"

                    for recipient in recipients:
                        ts = datetime.now().strftime("%H:%M:%S")
                        if LastPerson07_send_with_retry(client, recipient, msg):
                            results_table.add_row(
                                str(msg.id), msg_type, str(recipient),
                                "[bold green]✓  Sent[/bold green]", ts
                            )
                            sent_count += 1
                        else:
                            results_table.add_row(
                                str(msg.id), msg_type, str(recipient),
                                "[bold red]✗  Failed[/bold red]", ts
                            )
                            fail_count += 1
                        progress.advance(fwd_task)

                except Exception as e:
                    results_table.add_row(
                        str(msg.id), "?", "—",
                        f"[red]✗  Error[/red]", datetime.now().strftime("%H:%M:%S")
                    )
                    console.print(f"  [red]✗  Processing error on msg {msg.id}: {e}[/red]")
                    fail_count += 1

            progress.update(fwd_task, description="[green]✓  Forwarding complete[/green]")

            # ── Save new last ID ─────────────────────────────────────────────
            LastPerson07_save_last_id(messages[0].id)

        finally:
            client.disconnect()

    # ── Results ───────────────────────────────────────────────────────────────
    console.print()
    console.print(results_table)
    console.print()

    # Summary panel
    summary_color = "green" if fail_count == 0 else "yellow"
    console.print(Panel(
        f"[bold green]✓  Sent    :[/bold green]  {sent_count}\n"
        f"[bold yellow]⊘  Skipped :[/bold yellow]  {skip_count}\n"
        f"[bold red]✗  Failed  :[/bold red]  {fail_count}",
        title=f"[{summary_color}]📊  Run Summary — LastPerson07[/{summary_color}]",
        border_style=summary_color,
        padding=(0, 4)
    ))
    console.print()


# ╔══════════════════════════════════════════════════════════════════════════════╗
#  ENTRY POINT
# ╚══════════════════════════════════════════════════════════════════════════════╝
if __name__ == "__main__":

    LastPerson07_print_banner()

    # ── Load environment variables ────────────────────────────────────────────
    api_id_cred    = int(os.environ.get("API_ID", 0))
    api_hash_cred  = os.environ.get("API_HASH", "")
    session_string = os.environ.get("SESSION_STRING", "")
    source_chat    = int(os.environ.get("SOURCE_CHAT_ID", 0))

    recipients_str = os.environ.get("RECIPIENT_IDS", "")
    recipients     = [int(r.strip()) for r in recipients_str.split(",") if r.strip()]

    # ── Validate config ───────────────────────────────────────────────────────
    if not LastPerson07_validate_config(
        api_id_cred, api_hash_cred, session_string, source_chat, recipients
    ):
        sys.exit(1)

    # ── Uncomment to generate session string (run locally once) ───────────────
    # LastPerson07_get_session(api_id_cred, api_hash_cred)

    # ── Uncomment to look up a Telegram user ──────────────────────────────────
    # LastPerson07_get_user_by_name(api_id_cred, api_hash_cred, session_string)

    # ── Run forwarder ─────────────────────────────────────────────────────────
    LastPerson07_forward_messages(
        api_id_cred, api_hash_cred,
        source_chat, recipients, session_string
    )

    console.print(Rule("[dim cyan]LastPerson07 — Done[/dim cyan]", style="cyan"))
    console.print()
