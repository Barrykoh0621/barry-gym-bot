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
GYM_HOURS         = os.environ.get("GYM_HOURS", "7:00am - 10:00pm")
GYM_PRICE         = os.environ.get("GYM_PRICE", "RM 60/month")
GYM_REG_FEE       = os.environ.get("GYM_REG_FEE", "RM 90")
GYM_REG_FEE_STUDENT = os.environ.get("GYM_REG_FEE_STUDENT", "RM 60")
GYM_LOCATION      = os.environ.get("GYM_LOCATION", "Palm Mall, Seremban")

# Payment info - set these in Render.com environment variables
BANK_NAME         = os.environ.get("BANK_NAME", "Public Bank")
BANK_ACCOUNT      = os.environ.get("BANK_ACCOUNT", "6474752824")
BANK_HOLDER       = os.environ.get("BANK_HOLDER", "Barry Gym")
QR_CODE_IMAGE_URL = os.environ.get("QR_CODE_IMAGE_URL", "")

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
    "map": "location", "direction": "location",
}

REPLIES = {
    "pricing": (
        f"Hi! Here are *{GYM_NAME}* membership details 💪\n\n"
        f"*Monthly Fee:*\n"
        f"• RM 60/month (all members)\n\n"
        f"*Registration Fee:*\n"
        f"• Regular: *{GYM_REG_FEE}* (one-time)\n"
        f"• Student: *{GYM_REG_FEE_STUDENT}* (one-time, student card required)\n\n"
        f"Reply *JOIN* to sign up! 😊"
    ),
    "hours": (
        f"*{GYM_NAME}* Operating Hours:\n\n"
        f"📅 Monday - Sunday: *{GYM_HOURS}*\n"
        f"📅 Public Holidays: *7:00am - 10:00pm*\n\n"
        f"See you at the gym! 💪"
    ),
    "join": (
        f"Welcome to *{GYM_NAME}*! 🎉\n\n"
        f"To join, visit us and bring your *IC (MyKad)*.\n\n"
        f"*Monthly Fee:* RM 60/month\n\n"
        f"*Registration Fee (one-time):*\n"
        f"• Regular: *{GYM_REG_FEE}*\n"
        f"• Student: *{GYM_REG_FEE_STUDENT}* (student card required)\n\n"
        f"*Hours:* Mon-Sun {GYM_HOURS}\n\n"
        f"📍 {GYM_LOCATION}\n\n"
        f"Call us: *{GYM_PHONE}* 🏋️"
    ),
    "renew": (
        f"Hi! Ready to renew your *{GYM_NAME}* membership? 💪\n\n"
        f"*Monthly Fee: RM 60/month*\n\n"
        f"─────────────────\n"
        f"💳 *Pay via Online Transfer:*\n"
        f"Bank: *{BANK_NAME}*\n"
        f"Account: *{BANK_ACCOUNT}*\n"
        f"Name: *{BANK_HOLDER}*\n"
        f"Ref: *Your name*\n\n"
        f"After payment, send your *receipt screenshot* here.\n"
        f"─────────────────\n\n"
        f"Or visit / call us: *{GYM_PHONE}* 🏋️"
    ),
    "location": (
        f"📍 *{GYM_NAME}*\n\n"
        f"*{GYM_LOCATION}*\n\n"
        f"Hours: Mon-Sun {GYM_HOURS}\n\n"
        f"Need directions? Call/WhatsApp: *{GYM_PHONE}* 🏋️"
    ),
}

DEFAULT_REPLY = (
    f"Hi! Welcome to *{GYM_NAME}*! 🏋️\n\n"
    f"How can we help you? Reply with a keyword:\n\n"
    f"• *PRICE* — Membership prices\n"
    f"• *HOURS* — Operating hours\n"
    f"• *JOIN* — New membership\n"
    f"• *RENEW* — Renew membership\n"
    f"• *LOCATION* — Find us\n\n"
    f"Or call/WhatsApp: *{GYM_PHONE}*"
)


def send_reply(phone, message):
    url     = f"{ULTRAMSG_API_URL}/messages/chat"
    payload = {"token": ULTRAMSG_TOKEN, "to": phone, "body": message, "priority": 1}
    r = requests.post(url, data=payload, timeout=10)
    return r.status_code, r.json()


def send_image(phone, image_url, caption=""):
    """Send QR code or image via UltraMsg."""
    url     = f"{ULTRAMSG_API_URL}/messages/image"
    payload = {"token": ULTRAMSG_TOKEN, "to": phone, "image": image_url,
               "caption": caption, "priority": 1}
    requests.post(url, data=payload, timeout=10)


GREETINGS = {"hi", "hello", "hey", "helo", "hai", "haii", "ello", "yo",
             "assalamualaikum", "slm", "hi there", "good morning", "good afternoon"}

def is_greeting(text):
    return text.strip().lower() in GREETINGS

def get_reply_category(text):
    text_lower = text.strip().lower()
    for keyword, category in KEYWORDS.items():
        if keyword in text_lower:
            return category
    return None


class WebhookHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(f"{GYM_NAME} WhatsApp Bot is LIVE! ✅".encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data     = json.loads(body)
            msg_data = data.get("data", {})
            from_num = msg_data.get("from", "")
            msg_type = msg_data.get("type", "")
            body_txt = msg_data.get("body", "").strip()

            # Skip: groups, empty messages
            if not (msg_type == "chat" and body_txt and "@g.us" not in from_num):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                return

            # Skip messages from the gym's own number (prevent loop)
            if GYM_PHONE in from_num:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                return

            print(f"[{datetime.now().strftime('%H:%M:%S')}] MSG from {from_num}: {body_txt}")

            category = get_reply_category(body_txt)

            # ONLY reply if: greeting OR keyword match — nothing else
            if is_greeting(body_txt):
                send_reply(from_num, DEFAULT_REPLY)

            elif category is not None:
                reply = REPLIES[category]
                send_reply(from_num, reply)
                if category == "renew" and QR_CODE_IMAGE_URL:
                    send_image(from_num, QR_CODE_IMAGE_URL,
                               f"Scan to pay — {BANK_NAME} ({BANK_HOLDER})")

            # All other messages → ignored (no auto reply)

        except Exception as e:
            print(f"Error: {e}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        pass  # suppress default server logs


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"{'='*50}")
    print(f"{GYM_NAME} WhatsApp Auto-Reply Bot")
    print(f"Running on port {port}...")
    print(f"Bank: {BANK_NAME} | Acc: {BANK_ACCOUNT}")
    print(f"{'='*50}")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()
