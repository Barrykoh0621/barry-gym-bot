"""
Barry's Gym - WhatsApp Auto Reply (Cloud Version)
Deploy this on Render.com for FREE - runs 24/7 without your computer.
"""

import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import requests
from datetime import datetime

# ============================================================
# CONFIG - Set these in Render.com environment variables
# ============================================================
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE", "instance169328")
ULTRAMSG_TOKEN    = os.environ.get("ULTRAMSG_TOKEN", "ifk8d1jpsnl540eb")
ULTRAMSG_API_URL  = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}"

GYM_NAME          = os.environ.get("GYM_NAME", "Barry's Gym")
GYM_PHONE         = os.environ.get("GYM_PHONE", "60122201096")
GYM_HOURS_WEEKDAY = os.environ.get("GYM_HOURS_WEEKDAY", "6:00am - 10:00pm")
GYM_HOURS_WEEKEND = os.environ.get("GYM_HOURS_WEEKEND", "7:00am - 8:00pm")
GYM_PRICE_REGULAR = os.environ.get("GYM_PRICE_REGULAR", "RM 100/month")
GYM_PRICE_STUDENT = os.environ.get("GYM_PRICE_STUDENT", "RM 60/month")

# ============================================================
# KEYWORDS & REPLIES (English only)
# ============================================================
KEYWORDS = {
    "price": "pricing", "fee": "pricing", "fees": "pricing",
    "cost": "pricing", "rate": "pricing", "how much": "pricing",
    "hour": "hours", "hours": "hours", "time": "hours",
    "open": "hours", "close": "hours", "timing": "hours", "operating": "hours",
    "join": "join", "register": "join", "signup": "join",
    "sign up": "join", "new member": "join", "membership": "join",
    "renew": "renew", "renewal": "renew", "extend": "renew",
    "location": "location", "where": "location", "address": "location",
}

REPLIES = {
    "pricing": (
        f"Hi! Thank you for your interest in *{GYM_NAME}*! 💪\n\n"
        f"*Membership Prices:*\n"
        f"• Regular: *{GYM_PRICE_REGULAR}*\n"
        f"• Student: *{GYM_PRICE_STUDENT}*\n\n"
        f"Reply *JOIN* to sign up, or contact us at {GYM_PHONE}!"
    ),
    "hours": (
        f"*{GYM_NAME}* Operating Hours:\n\n"
        f"📅 Monday - Friday: *{GYM_HOURS_WEEKDAY}*\n"
        f"📅 Saturday - Sunday: *{GYM_HOURS_WEEKEND}*\n"
        f"📅 Public Holidays: *8:00am - 6:00pm*\n\n"
        f"See you at the gym! 💪"
    ),
    "join": (
        f"Welcome to *{GYM_NAME}*! 🎉\n\n"
        f"*To join, visit us with your IC.*\n\n"
        f"*Membership Plans:*\n"
        f"• Regular: *{GYM_PRICE_REGULAR}*\n"
        f"• Student: *{GYM_PRICE_STUDENT}* (student card required)\n\n"
        f"*Opening Hours:*\n"
        f"Mon-Fri: {GYM_HOURS_WEEKDAY}\n"
        f"Sat-Sun: {GYM_HOURS_WEEKEND}\n\n"
        f"Call us: {GYM_PHONE} 🏋️"
    ),
    "renew": (
        f"Hi! To renew your *{GYM_NAME}* membership:\n\n"
        f"1. Visit us at the gym, OR\n"
        f"2. Call/WhatsApp: *{GYM_PHONE}*\n\n"
        f"*Renewal Prices:*\n"
        f"• Regular: *{GYM_PRICE_REGULAR}*\n"
        f"• Student: *{GYM_PRICE_STUDENT}*\n\n"
        f"We'll sort you out quickly! 💪"
    ),
    "location": (
        f"*{GYM_NAME}* is located in Seremban, Negeri Sembilan.\n\n"
        f"📍 For exact directions, call us at *{GYM_PHONE}* and we'll guide you! 🏋️"
    ),
}

DEFAULT_REPLY = (
    f"Hi! Welcome to *{GYM_NAME}*! 🏋️\n\n"
    f"How can we help you?\n\n"
    f"Type any keyword:\n"
    f"• *PRICE* - Membership prices\n"
    f"• *HOURS* - Operating hours\n"
    f"• *JOIN* - New membership\n"
    f"• *RENEW* - Renew membership\n"
    f"• *LOCATION* - Find us\n\n"
    f"Or call/WhatsApp: *{GYM_PHONE}*"
)


def send_reply(phone, message):
    url     = f"{ULTRAMSG_API_URL}/messages/chat"
    payload = {"token": ULTRAMSG_TOKEN, "to": phone, "body": message, "priority": 1}
    r = requests.post(url, data=payload, timeout=10)
    return r.status_code, r.json()


def get_reply(text):
    text_lower = text.strip().lower()
    for keyword, category in KEYWORDS.items():
        if keyword in text_lower:
            return REPLIES[category]
    return DEFAULT_REPLY


class WebhookHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"{GYM_NAME} WhatsApp Bot is running!".encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data     = json.loads(body)
            msg_data = data.get("data", {})
            from_num = msg_data.get("from", "")
            msg_type = msg_data.get("type", "")
            body_txt = msg_data.get("body", "")

            if msg_type == "chat" and body_txt and "@g.us" not in from_num:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] From {from_num}: {body_txt}")
                reply = get_reply(body_txt)
                send_reply(from_num, reply)

        except Exception as e:
            print(f"Error: {e}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"{GYM_NAME} WhatsApp Bot running on port {port}...")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()
