"""Helper: prints the webhook URL + verify token to paste in Meta App Dashboard.

Meta requires manual configuration through the dashboard (no API). Run this
script to get the values to paste:
    https://developers.facebook.com → Your App → WhatsApp → Configuration
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ENV = Path(__file__).resolve().parents[1] / "backend" / ".env"
load_dotenv(ENV)

PUBLIC_URL = os.getenv("PUBLIC_WEBHOOK_URL", "").rstrip("/")
VERIFY = os.getenv("WHATSAPP_VERIFY_TOKEN", "")

print("=" * 60)
print("Paste these in Meta App → WhatsApp → Configuration")
print("=" * 60)
print(f"Callback URL  : {PUBLIC_URL}/webhooks/whatsapp")
print(f"Verify Token  : {VERIFY}")
print("=" * 60)
print("After clicking 'Verify and Save', subscribe to the 'messages' field.")
