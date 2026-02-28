#!/usr/bin/env python3
"""
Run this script once to register your webhook with Telegram.
Usage: python setup_webhook.py <YOUR_PUBLIC_URL>
Example: python setup_webhook.py https://myapp.example.com
"""
import sys
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not set in .env")
    sys.exit(1)

if len(sys.argv) < 2:
    print("Usage: python setup_webhook.py <YOUR_PUBLIC_URL>")
    sys.exit(1)

base_url = sys.argv[1].rstrip("/")
webhook_url = f"{base_url}/api/telegram/webhook"

resp = httpx.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
    json={"url": webhook_url, "allowed_updates": ["message"]},
)
data = resp.json()
if data.get("ok"):
    print(f"✅ Webhook set: {webhook_url}")
else:
    print(f"❌ Failed: {data}")
