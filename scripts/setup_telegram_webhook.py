"""Register Telegram bot webhooks pointing to our public URL (ngrok).

Usage:
    python scripts/setup_telegram_webhook.py
"""
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "backend" / ".env"
load_dotenv(ENV)

PUBLIC_URL = os.getenv("PUBLIC_WEBHOOK_URL", "").rstrip("/")
MA2E_TOKEN = os.getenv("TELEGRAM_TOKEN_MA2E", "")

if not PUBLIC_URL:
    print("❌ PUBLIC_WEBHOOK_URL not set in backend/.env (run ngrok and paste URL)")
    sys.exit(1)


def register(label: str, token: str):
    if not token:
        print(f"⚠️  Skipping {label} (no token)")
        return
    suffix = token.split(":")[0]
    webhook_url = f"{PUBLIC_URL}/webhooks/telegram/{suffix}"
    resp = httpx.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={"url": webhook_url, "drop_pending_updates": True},
        timeout=10.0,
    )
    print(f"➡️  {label}: {webhook_url}")
    print(f"   Response: {resp.status_code} {resp.text}")


if __name__ == "__main__":
    register("MA2E", MA2E_TOKEN)
