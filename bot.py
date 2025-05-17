import os
import json
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta, timezone

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
ALLOWED_USERNAME = ["laurenkoek", "nigelus"]

# Logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Google Calendar Setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
calendar_service = build('calendar', 'v3', credentials=creds)

class CalendarEvent:
    """
    Represents a single Google Calendar event and provides formatting utilities.
    Supports both all-day and timed events.
    """
    def __init__(self, raw_event):
        """
        Initialize a CalendarEvent from a raw Google Calendar API event dictionary.
        
        Args:
            raw_event (dict): The raw event data from the Google Calendar API.
        """
        self.summary = raw_event.get("summary", "No title")
        self.is_all_day = False

        start_raw = raw_event['start'].get('dateTime') or raw_event['start'].get('date')
        end_raw = raw_event['end'].get('dateTime') or raw_event['end'].get('date')

        try:
            self.start = datetime.fromisoformat(start_raw)
            self.end = datetime.fromisoformat(end_raw)
        except ValueError:
            # All-day event
            self.start = datetime.strptime(start_raw, "%Y-%m-%d")
            self.end = datetime.strptime(end_raw, "%Y-%m-%d")
            self.is_all_day = True

    def format(self) -> str:
        """
        Format the event into a visually aligned multi-line string for Telegram Markdown.
        Includes date, time, and summary with emojis for readability.

        Returns:
            str: Formatted event string with aligned layout.
        """
        if self.is_all_day:
            date_str = self.start.strftime("%a %d %b")
            return f"{date_str}   All Day\n            - {self.summary}"
        else:
            date_str = self.start.strftime("%a %d %b")
            time_str = f"{self.start.strftime('%I:%M %p')} - {self.end.strftime('%I:%M %p')}"
            return f"{date_str} |   *{self.summary}*\n            ({time_str})\n"



def send_message(chat_id, text, markdown=False):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    if markdown:
        payload["parse_mode"] = "Markdown"
    response = requests.post(url, json=payload)
    if not response.ok:
        logger.error(f"Telegram send_message failed: {response.text}")
    return response

def get_upcoming_events():
    now = datetime.utcnow().isoformat() + 'Z'
    events_result = calendar_service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=5,
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    items = events_result.get('items', [])
    if not items:
        return "No upcoming events found!"

    message = ""
    for raw_event in items:
        event = CalendarEvent(raw_event)
        message += event.format() + "\n"

    return message


def get_events_between(start_dt: datetime, end_dt: datetime) -> str:
    """
    Retrieves and formats Google Calendar events between two datetime ranges.

    Args:
        start_dt (datetime): Start of the time range (inclusive).
        end_dt (datetime): End of the time range (exclusive).

    Returns:
        str: A formatted list of events or None if no events are found.
    """
    events_result = calendar_service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
        singleEvents=True,
        orderBy='startTime'
    ).execute()

    events = events_result.get('items', [])
    if not events:
        return None

    return "\n".join(CalendarEvent(event).format() for event in events)


def get_today_events() -> str:
    """
    Get all events scheduled for today (midnight to midnight UTC).

    Returns:
        str: Formatted string of today's events or a fallback message.
    """
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return get_events_between(start, end) or "No events scheduled today!"


def get_week_events() -> str:
    """
    Get all events scheduled from today until the end of the week (Sunday).

    Returns:
        str: Formatted string of this week's remaining events or a fallback message.
    """
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    days_until_sunday = (6 - now.weekday()) % 7 + 1  # Monday=0...Sunday=6
    end = start + timedelta(days=days_until_sunday)
    return get_events_between(start, end) or "No events scheduled for the rest of the week!"

def lambda_handler(event, context):
    try:
        logger.info("Incoming event: " + json.dumps(event))

        body = json.loads(event['body'])
        message = body.get('message', {})
        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id')
        username = message.get('from', {}).get('username')
        user_id = message.get('from', {}).get('id')

        logger.info(f"chat_id: {chat_id}, user_id: {user_id}, username: {username}, text: {text}")

        if username not in ALLOWED_USERNAME:
            send_message(chat_id, "🚫 Sorry, you're not allowed to use this bot.")
            return {'statusCode': 200, 'body': 'Unauthorized'}

        if text == "/start":
            send_message(chat_id, f"👋 Hi @{username}! I can help manage your calendar.\nTry /help to view all available commands.")
        elif text == "/upcoming":
            msg = get_upcoming_events()
            send_message(chat_id, f"*Upcoming Events:*\n\n{msg}", markdown=True)
        elif text == "/today":
            msg = get_today_events()
            send_message(chat_id, f"*Today's Schedule:*\n\n{msg}", markdown=True)
        elif text == "/week":
            msg = get_week_events()
            send_message(chat_id, f"*This Week's Events:*\n\n{msg}", markdown=True)
        elif text == "/help":
            msg = (
                "*Available Commands:*\n"
                "/start - Welcome\n"
                "/upcoming - View next 5 events\n"
                "/today - View today's events\n"
                "/week - View this week's events"
            )
            send_message(chat_id, msg, markdown=True)
        else:
            send_message(chat_id, "❓ Unknown command. Try /help.")

        return {'statusCode': 200, 'body': 'OK'}

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        return {'statusCode': 500, 'body': 'Internal Server Error'}

