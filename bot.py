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

    events = events_result.get('items', [])
    if not events:
        return "🗓 No upcoming events found!"

    message = "📅 *Next Events:*\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        start_time = datetime.fromisoformat(start).strftime("%d %b %I:%M %p")
        summary = event.get("summary", "No title")
        message += f"• {start_time} – {summary}\n"
    return message

def get_events_between(start_dt: datetime, end_dt: datetime):
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

    message = ""
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        start_time = datetime.fromisoformat(start).strftime("%a %d %b %I:%M %p")
        summary = event.get("summary", "No title")
        message += f"• {start_time} – {summary}\n"
    return message


def get_today_events():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    message = get_events_between(start, end)
    return message or "No events scheduled today!"


def get_week_events():
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    days_until_sunday = (6 - now.weekday()) % 7 + 1  # Monday=0...Sunday=6
    end = start + timedelta(days=days_until_sunday)
    message = get_events_between(start, end)
    return message or "No events scheduled for the rest of the week!"

def lambda_handler(event, context):
    try:
        logger.info("Incoming event: " + json.dumps(event))
        body = json.loads(event['body'])
        message = body.get('message', {})
        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id')
        username = message.get('from', {}).get('username')

        logger.info(f"chat_id: {chat_id}, username: {username}, text: {text}")

        if username not in ALLOWED_USERNAME:
            send_message(chat_id, "🚫 Sorry, you're not allowed to use this bot.")
            return {'statusCode': 200, 'body': 'Unauthorized'}

        if text == "/start":
            send_message(chat_id, "👋 Hi Lauren! I can help manage your calendar.\nTry /help to view all available commands.")
        elif text == "/upcoming":
            msg = get_upcoming_events()
            send_message(chat_id, msg, markdown=True)
        elif text == "/today":
            msg = get_today_events()
            send_message(chat_id, f"📆 *Today's Schedule:*\n\n{msg}", markdown=True)
        elif text == "/week":
            msg = get_week_events()
            send_message(chat_id, f"🗓 *This Week's Events:*\n\n{msg}", markdown=True)
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
