"""
BotMate - WhatsApp Auto Reply (Cloud Version)
Client: Hung Ta Instrument
"""

import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import requests
from datetime import datetime

# ============================================================
# CONFIG
# ============================================================
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE", "instance169328")
ULTRAMSG_TOKEN    = os.environ.get("ULTRAMSG_TOKEN", "ifk8d1jpsnl540eb")
ULTRAMSG_API_URL  = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}"

COMPANY_NAME  = os.environ.get("COMPANY_NAME", "Hung Ta Instrument")
COMPANY_PHONE = os.environ.get("COMPANY_PHONE", "60122201096")
OFFICE_HOURS  = os.environ.get("OFFICE_HOURS", "Monday - Friday: 8:30am - 6:00pm")
OFFICE_CLOSED = os.environ.get("OFFICE_CLOSED", "Saturday & Sunday: Closed")

# ============================================================
# KEYWORDS & REPLIES
# ============================================================
KEYWORDS = {
    # Request for Quotation
    "quotation": "rfq", "quote": "rfq", "rfq": "rfq",
    "request for quotation": "rfq", "price list": "rfq",
    "harga": "rfq", "sebut harga": "rfq",
    # Calibration
    "calibration": "calibration", "calibrate": "calibration",
    "kalibrasi": "calibration", "cal": "calibration",
    "certificate": "calibration", "cert": "calibration",
    # Spare Part
    "spare part": "sparepart", "sparepart": "sparepart",
    "spare": "sparepart", "parts": "sparepart",
    "replacement": "sparepart", "part": "sparepart",
    "alat ganti": "sparepart",
}

REPLIES = {
    "rfq": (
        f"Hi! Thank you for contacting *{COMPANY_NAME}* 😊\n\n"
        f"📋 *Request for Quotation (RFQ)*\n\n"
        f"To prepare your quotation, please provide:\n"
        f"1️⃣ Instrument/Equipment name & model\n"
        f"2️⃣ Brand (if any)\n"
        f"3️⃣ Quantity required\n"
        f"4️⃣ Your company name & address\n\n"
        f"Our team will get back to you within *1 working day* ✅\n\n"
        f"📞 Call us: *{COMPANY_PHONE}*\n"
        f"🕐 {OFFICE_HOURS}\n"
        f"🚫 {OFFICE_CLOSED}"
    ),
    "calibration": (
        f"Hi! Thank you for contacting *{COMPANY_NAME}* 😊\n\n"
        f"🔬 *Calibration Services*\n\n"
        f"To process your calibration request, please provide:\n"
        f"1️⃣ Instrument name & model\n"
        f"2️⃣ Brand & serial number\n"
        f"3️⃣ Quantity of instruments\n"
        f"4️⃣ Calibration certificate required? (Yes/No)\n"
        f"5️⃣ Your company name\n\n"
        f"Our team will get back to you within *1 working day* ✅\n\n"
        f"📞 Call us: *{COMPANY_PHONE}*\n"
        f"🕐 {OFFICE_HOURS}\n"
        f"🚫 {OFFICE_CLOSED}"
    ),
    "sparepart": (
        f"Hi! Thank you for contacting *{COMPANY_NAME}* 😊\n\n"
        f"🔧 *Spare Parts Enquiry*\n\n"
        f"To help you find the right spare part, please provide:\n"
        f"1️⃣ Instrument/Equipment name & model\n"
        f"2️⃣ Brand & serial number\n"
        f"3️⃣ Part name or part number (if known)\n"
        f"4️⃣ Quantity required\n"
        f"5️⃣ Your company name\n\n"
        f"Our team will get back to you within *1 working day* ✅\n\n"
        f"📞 Call us: *{COMPANY_PHONE}*\n"
        f"🕐 {OFFICE_HOURS}\n"
        f"🚫 {OFFICE_CLOSED}"
    ),
}

DEFAULT_REPLY = (
    f"Hi! Welcome to *{COMPANY_NAME}* 👋\n\n"
    f"How can we help you today? Please reply with a keyword:\n\n"
    f"📋 *QUOTATION* — Request for Quotation\n"
    f"🔬 *CALIBRATION* — Calibration Services\n"
    f"🔧 *SPARE PART* — Spare Parts Enquiry\n\n"
    f"🕐 Office Hours:\n"
    f"{OFFICE_HOURS}\n"
    f"🚫 {OFFICE_CLOSED}\n\n"
    f"📞 Call us: *{COMPANY_PHONE}*"
)


def send_reply(phone, message):
    url     = f"{ULTRAMSG_API_URL}/messages/chat"
    payload = {"token": ULTRAMSG_TOKEN, "to": phone, "body": message, "priority": 1}
    r = requests.post(url, data=payload, timeout=10)
    return r.status_code, r.json()


GREETINGS = {"hi", "hello", "hey", "helo", "hai", "haii", "ello", "yo",
             "assalamualaikum", "slm", "hi there", "good morning", "good afternoon",
             "selamat pagi", "selamat petang", "wassup", "wsp"}

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
        self.wfile.write(f"{COMPANY_NAME} WhatsApp Bot is LIVE! ✅".encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body   = self.rfile.read(length)
        try:
            data     = json.loads(body)
            msg_data = data.get("data", {})
            from_num = msg_data.get("from", "")
            msg_type = msg_data.get("type", "")
            body_txt = msg_data.get("body", "").strip()

            if not (msg_type == "chat" and body_txt and "@g.us" not in from_num):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                return

            if COMPANY_PHONE.replace("-","") in from_num:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"OK")
                return

            print(f"[{datetime.now().strftime('%H:%M:%S')}] MSG from {from_num}: {body_txt}")

            category = get_reply_category(body_txt)

            if is_greeting(body_txt):
                send_reply(from_num, DEFAULT_REPLY)
            elif category is not None:
                reply = REPLIES[category]
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
    print(f"{'='*50}")
    print(f"{COMPANY_NAME} WhatsApp Bot")
    print(f"Running on port {port}...")
    print(f"{'='*50}")
    HTTPServer(("0.0.0.0", port), WebhookHandler).serve_forever()
