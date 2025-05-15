import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from google.oauth2 import service_account
from googleapiclient.discovery import build

# Load .env
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Google Calendar API
SCOPES = ['https://www.googleapis.com/auth/calendar']
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
calendar_service = build('calendar', 'v3', credentials=creds)

# Only allow a specific user
ALLOWED_USERNAME = ["laurenkoek", "nigelus"]

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username not in ALLOWED_USERNAME:
        await update.message.reply_text("🚫 Sorry, you're not allowed to use this bot.")
        return

    await update.message.reply_text("👋 Hi Lauren! I can help manage your calendar.\nTry /help to view all available commands.")

# Command: /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username not in ALLOWED_USERNAME:
        await update.message.reply_text("🚫 You're not allowed to use this bot.")
        return

    message = (
        """🤖 *Available Commands:*\n
        /start - Welcome message\n
        /upcoming - View next 5 events\n"""
    )
    await update.message.reply_text(message)

# Command: /upcoming
async def upcoming(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username not in ALLOWED_USERNAME:
        await update.message.reply_text("🚫 Sorry, you're not allowed to use this bot.")
        return

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
        await update.message.reply_text("🗓 No upcoming events found!")
        return

    message = "📅 *Next Events:*\n"
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        start_time = datetime.fromisoformat(start).strftime("%d %b %I:%M %p")
        summary = event.get("summary", "No title")
        message += f"• {start_time} – {summary}\n"

    await update.message.reply_text(message, parse_mode='Markdown')


# Run the bot
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("upcoming", upcoming))
    logger.info("🤖 Bot started...")
    app.run_polling()
