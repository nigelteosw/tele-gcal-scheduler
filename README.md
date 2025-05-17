# Telegram Google Calendar Bot

This is a Telegram bot that integrates with Google Calendar to provide users with daily, weekly, and upcoming event summaries. It supports:

* Secure Telegram command interaction (`/today`, `/week`, `/upcoming`)
* Daily schedule auto-sending via AWS EventBridge and Lambda
* Clean Markdown formatting for easy reading

---

## Features

* View the next 5 events: `/upcoming`
* View today’s agenda: `/today`
* View the rest of the week: `/week`
* Automatically receive a daily schedule at 8 AM (via EventBridge Scheduler)

---

## Setup Guide

### 1. Google Cloud Platform Configuration

#### a. Enable Google Calendar API

1. Visit [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Navigate to **APIs & Services > Library**.
4. Enable the **Google Calendar API**.

#### b. Create a Service Account

1. Go to **IAM & Admin > Service Accounts**.
2. Create a new service account with basic description.
3. After creation, go to the **"Keys"** tab.
4. Click **"Add Key" > "Create new key"**, choose **JSON**, and download it.

> Rename the downloaded key file to `creds.json`.

#### c. Share Your Calendar with the Service Account

1. Open your Google Calendar in a browser.
2. Click **Settings > Share with specific people**.
3. Add the **service account email** (e.g., `my-bot@my-project.iam.gserviceaccount.com`) with **"Make changes and manage sharing"** permissions.

---

### 2. AWS Setup

#### a. Create a Lambda Function

1. Go to [AWS Lambda Console](https://console.aws.amazon.com/lambda/).
2. Create a new function using Python 3.10.
3. Set up environment variables:

   * `TELEGRAM_BOT_TOKEN` — Your bot token from BotFather
   * `GOOGLE_CALENDAR_ID` — The ID of the calendar to query
   * `SERVICE_ACCOUNT_FILE` — Must be set to `creds.json`
   * `JOB_CHAT_ID` — Telegram chat ID to receive scheduled messages

#### b. Set Up IAM Permissions

Make sure your Lambda execution role has the following:

* Basic Lambda execution permissions (`AWSLambdaBasicExecutionRole`)
* A resource-based policy that allows EventBridge Scheduler to invoke the function

You also need to add this to your **Lambda resource policy**:

```json
{
  "Effect": "Allow",
  "Principal": {
    "Service": "scheduler.amazonaws.com"
  },
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:<region>:<account_id>:function:<your-function-name>",
  "Condition": {
    "ArnLike": {
      "AWS:SourceArn": "arn:aws:scheduler:<region>:<account_id>:schedule/default/<schedule-name>"
    }
  }
}
```

#### c. Set Up EventBridge Scheduler (Optional)

1. Go to [EventBridge Scheduler](https://console.aws.amazon.com/scheduler/home).
2. Create a new schedule with the cron expression `0 8 * * ? *` to run at 8 AM SG time daily.
3. Set the target to your Lambda function.
4. Provide the following as the input payload:

```json
{
  "source": "aws.scheduler",
  "job": "daily_calendar"
}
```

---

## 3. Building the Lambda Deployment Package

Use the provided PowerShell script to package your code and dependencies into a Lambda-compatible zip file.

### Requirements

* Python 3.10 installed
* `pip` available
* A `requirements.txt` file with dependencies listed (e.g. `google-api-python-client`, `python-dotenv`, `requests`)

### Steps

1. Open PowerShell and run:

```powershell
# build-lambda.ps1

Remove-Item -Recurse -Force .\lambda_package -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path .\lambda_package | Out-Null

pip install -r requirements.txt -t .\lambda_package

Copy-Item .\bot.py .\lambda_package\
Copy-Item .\creds.json .\lambda_package\

Compress-Archive -Path .\lambda_package\* -DestinationPath .\lambda-deploy.zip -Force
```

2. Upload `lambda-deploy.zip` to your Lambda function.

---

## Testing

To test locally:

```python
# test_lambda.py
from bot import lambda_handler

event = {
    "body": json.dumps({
        "message": {
            "text": "/today",
            "chat": {"id": "<YOUR_TELEGRAM_CHAT_ID>"},
            "from": {"username": "<YOUR_USERNAME>"}
        }
    })
}

class Context: pass
print(lambda_handler(event, Context()))
```

To test the scheduler logic:

```python
event = {
    "source": "aws.scheduler",
    "job": "daily_calendar"
}
print(lambda_handler(event, Context()))
```

---

## Notes

* This bot is **hardcoded to allow only specific Telegram usernames** (`ALLOWED_USERNAME` list).
* It uses `parse_mode='Markdown'` to format messages, so avoid special characters in summaries unless escaped.
* You can scale this to support multiple users by building a chat ID registry or linking users to calendars.


