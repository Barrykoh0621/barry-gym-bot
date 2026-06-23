"""
Barry's Gym - Record Management App
Web dashboard + WhatsApp bot (UltraMsg) + 24/7 auto-reminder scheduler
"""

import os
import atexit
import requests
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import gym_db

gym_db.init_db()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "barry-gym-secret-2024")

# ── Config ────────────────────────────────────────────────────
ULTRAMSG_INSTANCE  = os.environ.get("ULTRAMSG_INSTANCE", "instance169328")
ULTRAMSG_TOKEN     = os.environ.get("ULTRAMSG_TOKEN", "ifk8d1jpsnl540eb")
ULTRAMSG_API_URL   = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}"

GYM_NAME           = os.environ.get("GYM_NAME", "Barry's Gym")
GYM_PHONE          = os.environ.get("GYM_PHONE", "60122201096")
GYM_HOURS_WEEKDAY  = os.environ.get("GYM_HOURS_WEEKDAY", "6:00am - 10:00pm")
GYM_HOURS_WEEKEND  = os.environ.get("GYM_HOURS_WEEKEND", "7:00am - 8:00pm")
GYM_PRICE_REGULAR  = os.environ.get("GYM_PRICE_REGULAR", "RM 100/month")
GYM_PRICE_STUDENT  = os.environ.get("GYM_PRICE_STUDENT", "RM 60/month")
BANK_NAME          = os.environ.get("BANK_NAME", "Public Bank")
BANK_ACCOUNT       = os.environ.get("BANK_ACCOUNT", "6474752824")
BANK_HOLDER        = os.environ.get("BANK_HOLDER", "Barry Gym")
QR_CODE_IMAGE_URL  = os.environ.get("QR_CODE_IMAGE_URL", "")

AMOUNT_MAP = {"regular": 100.0, "student": 60.0}


# ── WhatsApp helpers ──────────────────────────────────────────

def send_whatsapp(phone, message):
    url     = f"{ULTRAMSG_API_URL}/messages/chat"
    payload = {"token": ULTRAMSG_TOKEN, "to": phone, "body": message, "priority": 1}
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.status_code
    except Exception as e:
        print(f"[WhatsApp] Send error: {e}")
        return 0


def send_whatsapp_image(phone, image_url, caption=""):
    url     = f"{ULTRAMSG_API_URL}/messages/image"
    payload = {"token": ULTRAMSG_TOKEN, "to": phone, "image": image_url, "caption": caption}
    try:
        r = requests.post(url, data=payload, timeout=10)
        return r.status_code
    except Exception as e:
        print(f"[WhatsApp] Image send error: {e}")
        return 0


# ── Scheduler: 24/7 Auto-Reminders ───────────────────────────

def _build_reminder_msg(member, days_left):
    name   = member["name"]
    expiry = member["expiry_date"]
    amount = "RM 60" if member["membership_type"] == "student" else "RM 100"
    if days_left == 7:
        return (
            f"Hi *{name}*! 👋\n\n"
            f"Friendly reminder: your *{GYM_NAME}* membership expires in *7 days* on {expiry}.\n\n"
            f"Renew now for {amount}/month and keep your streak going! 💪\n\n"
            f"💳 Reply *PAYMENT* for bank details.\n"
            f"📞 Contact: *{GYM_PHONE}*"
        )
    elif days_left == 3:
        return (
            f"⚠️ *Urgent, {name}!*\n\n"
            f"Your *{GYM_NAME}* membership expires in *3 days* on {expiry}.\n\n"
            f"Renew now for {amount}/month — don't lose your access!\n\n"
            f"💳 Reply *PAYMENT* for bank details.\n"
            f"📞 Contact: *{GYM_PHONE}*"
        )
    else:
        return (
            f"🚨 *Last Chance, {name}!*\n\n"
            f"Your *{GYM_NAME}* membership *expires TODAY* ({expiry}).\n\n"
            f"Reply *PAYMENT* right now to renew for {amount}/month and keep training! 💪\n\n"
            f"📞 Contact: *{GYM_PHONE}*"
        )


def _build_overdue_msg(member):
    name   = member["name"]
    expiry = member["expiry_date"]
    amount = "RM 60" if member["membership_type"] == "student" else "RM 100"
    today  = date.today()
    days   = (today - date.fromisoformat(expiry)).days
    return (
        f"Hi *{name}* 🏋️\n\n"
        f"Your *{GYM_NAME}* membership expired *{days} days ago* on {expiry}.\n\n"
        f"We miss you! Renew for {amount}/month to get back in the gym.\n\n"
        f"💳 Reply *PAYMENT* for bank details.\n"
        f"📞 Contact: *{GYM_PHONE}*\n\n"
        f"Come back stronger! 💪"
    )


def _run_daily_jobs():
    """Runs at 9:00 AM MYT daily — the core revenue engine."""
    print(f"[Scheduler] Daily jobs started at {datetime.now()}")

    # 1. Auto-mark overdue members
    count = gym_db.auto_mark_overdue()
    print(f"[Scheduler] Marked {count} members as overdue")

    # 2. Send expiry reminders (7 days, 3 days, today)
    sent = 0
    for days_left in (7, 3, 0):
        for m in gym_db.get_members_expiring_in_days(days_left):
            send_whatsapp(m["phone"], _build_reminder_msg(m, days_left))
            sent += 1

    # 3. Chase overdue members (every 3 days after expiry)
    for m in gym_db.get_members_overdue_for_chasing():
        send_whatsapp(m["phone"], _build_overdue_msg(m))
        sent += 1

    print(f"[Scheduler] Sent {sent} WhatsApp reminders")


# Start scheduler — safe with gunicorn --workers 1 --preload
_scheduler = BackgroundScheduler()
_scheduler.add_job(
    _run_daily_jobs,
    trigger=CronTrigger(hour=9, minute=0, timezone="Asia/Kuala_Lumpur")
)
_scheduler.start()
atexit.register(lambda: _scheduler.running and _scheduler.shutdown(wait=False))


# ── WhatsApp keyword bot ──────────────────────────────────────

GREETINGS = {
    "hi", "hello", "hey", "helo", "hai", "haii", "ello", "yo",
    "assalamualaikum", "slm", "hi there", "good morning", "good afternoon",
    "selamat pagi", "selamat petang", "wassup", "wsp",
}

KEYWORDS = {
    "membership": "membership", "join": "membership", "daftar": "membership",
    "member": "membership", "price": "membership", "harga": "membership",
    "payment": "payment", "bayar": "payment", "pay": "payment",
    "bank": "payment", "transfer": "payment", "qr": "payment",
    "hours": "hours", "masa": "hours", "waktu": "hours", "time": "hours",
    "open": "hours", "buka": "hours", "close": "buka",
    "status": "status", "expiry": "status", "expired": "status",
    "tamat": "status", "tarikh": "status",
    "checkin": "checkin", "check in": "checkin", "masuk": "checkin",
    "checkout": "checkout", "check out": "checkout", "keluar": "checkout",
    "renew": "payment", "renewal": "payment", "perpanjang": "payment",
}

MENU = (
    f"👋 Welcome to *{GYM_NAME}*!\n\n"
    f"How can we help you? Reply with:\n\n"
    f"🏋️ *MEMBERSHIP* — Pricing & plans\n"
    f"💳 *PAYMENT* — Bank & payment details\n"
    f"🕐 *HOURS* — Gym opening hours\n"
    f"📋 *STATUS* — Check your membership status\n"
    f"✅ *CHECKIN* — Record your gym check-in\n"
    f"🚪 *CHECKOUT* — Record your gym check-out\n\n"
    f"📞 Contact: *{GYM_PHONE}*"
)

MEMBERSHIP_REPLY = (
    f"🏋️ *{GYM_NAME} — Membership Plans*\n\n"
    f"💰 Regular Member: *{GYM_PRICE_REGULAR}*\n"
    f"🎓 Student Member: *{GYM_PRICE_STUDENT}*\n\n"
    f"✅ Full gym access\n"
    f"✅ All equipment & facilities\n\n"
    f"To register, please provide:\n"
    f"1️⃣ Full name\n"
    f"2️⃣ Phone number\n"
    f"3️⃣ Membership type (Regular / Student)\n\n"
    f"📞 Call us: *{GYM_PHONE}*\n"
    f"🕐 Weekdays: {GYM_HOURS_WEEKDAY}\n"
    f"🕐 Weekends: {GYM_HOURS_WEEKEND}"
)

PAYMENT_REPLY = (
    f"💳 *{GYM_NAME} — Payment Details*\n\n"
    f"🏦 Bank: *{BANK_NAME}*\n"
    f"📄 Account: *{BANK_ACCOUNT}*\n"
    f"👤 Name: *{BANK_HOLDER}*\n\n"
    f"After payment, please send:\n"
    f"1️⃣ Payment screenshot\n"
    f"2️⃣ Your full name\n"
    f"3️⃣ Month of payment\n\n"
    f"Thank you! 🙏"
)

HOURS_REPLY = (
    f"🕐 *{GYM_NAME} — Opening Hours*\n\n"
    f"📅 Monday – Friday: *{GYM_HOURS_WEEKDAY}*\n"
    f"📅 Saturday – Sunday: *{GYM_HOURS_WEEKEND}*\n\n"
    f"📞 For enquiries: *{GYM_PHONE}*"
)


def handle_status(phone):
    member = gym_db.get_member_by_phone(phone)
    if not member:
        return (
            f"❌ *No membership found* for this number.\n\n"
            f"To register, reply *MEMBERSHIP* for our plans.\n"
            f"📞 Contact: *{GYM_PHONE}*"
        )
    today   = date.today().isoformat()
    expired = member["expiry_date"] < today
    s_icon  = "✅" if not expired else "❌"
    s_text  = "Active" if not expired else "Expired"
    p_icon  = "✅" if member["payment_status"] == "paid" else "⚠️"
    return (
        f"📋 *Membership Status*\n\n"
        f"👤 Name: *{member['name']}*\n"
        f"🏷️ Plan: *{member['membership_type'].title()}*\n"
        f"{s_icon} Status: *{s_text}*\n"
        f"📅 Expiry: *{member['expiry_date']}*\n"
        f"{p_icon} Payment: *{member['payment_status'].title()}*\n\n"
        f"📞 Enquiries: *{GYM_PHONE}*"
    )


def handle_checkin(phone):
    member = gym_db.get_member_by_phone(phone)
    if not member:
        return (
            f"❌ You are *not registered* as a member.\n"
            f"Reply *MEMBERSHIP* to see our plans.\n"
            f"📞 Contact: *{GYM_PHONE}*"
        )
    today = date.today().isoformat()
    if member["expiry_date"] < today:
        return (
            f"⚠️ Hi *{member['name']}*, your membership has *expired*.\n"
            f"Expiry: {member['expiry_date']}\n\n"
            f"Please renew to continue using the gym.\n"
            f"Reply *PAYMENT* for payment details.\n"
            f"📞 Contact: *{GYM_PHONE}*"
        )
    ok  = gym_db.checkin(member["id"])
    now = datetime.now().strftime("%I:%M %p")
    if ok:
        return (
            f"✅ *Check-in recorded!*\n\n"
            f"👤 {member['name']}\n"
            f"🕐 Time: {now}\n"
            f"💪 Have a great workout!"
        )
    return (
        f"ℹ️ Hi *{member['name']}*, you're already checked in today.\n"
        f"Reply *CHECKOUT* when you leave."
    )


def handle_checkout(phone):
    member = gym_db.get_member_by_phone(phone)
    if not member:
        return (
            f"❌ You are *not registered* as a member.\n"
            f"📞 Contact: *{GYM_PHONE}*"
        )
    ok  = gym_db.checkout(member["id"])
    now = datetime.now().strftime("%I:%M %p")
    if ok:
        return (
            f"🚪 *Check-out recorded!*\n\n"
            f"👤 {member['name']}\n"
            f"🕐 Time: {now}\n"
            f"See you next time! 💪"
        )
    return (
        f"ℹ️ Hi *{member['name']}*, no active check-in found today.\n"
        f"Reply *CHECKIN* to check in."
    )


# ── WhatsApp webhook ──────────────────────────────────────────

@app.route("/webhook", methods=["GET"])
def webhook_verify():
    return f"{GYM_NAME} WhatsApp Bot is LIVE! ✅", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        data     = request.get_json(force=True) or {}
        msg_data = data.get("data", {})
        from_num = msg_data.get("from", "")
        msg_type = msg_data.get("type", "")
        body_txt = msg_data.get("body", "").strip()

        if not (msg_type == "chat" and body_txt and "@g.us" not in from_num):
            return "OK", 200
        if GYM_PHONE.replace("-", "") in from_num:
            return "OK", 200

        print(f"[{datetime.now().strftime('%H:%M:%S')}] MSG from {from_num}: {body_txt}")
        text_lower = body_txt.strip().lower()

        if text_lower in GREETINGS:
            send_whatsapp(from_num, MENU)
            return "OK", 200

        category = None
        for keyword, cat in KEYWORDS.items():
            if keyword in text_lower:
                category = cat
                break

        if category == "membership":
            send_whatsapp(from_num, MEMBERSHIP_REPLY)
        elif category == "payment":
            send_whatsapp(from_num, PAYMENT_REPLY)
            if QR_CODE_IMAGE_URL:
                send_whatsapp_image(from_num, QR_CODE_IMAGE_URL, "Scan to pay 🙏")
        elif category == "hours":
            send_whatsapp(from_num, HOURS_REPLY)
        elif category == "status":
            send_whatsapp(from_num, handle_status(from_num))
        elif category == "checkin":
            send_whatsapp(from_num, handle_checkin(from_num))
        elif category == "checkout":
            send_whatsapp(from_num, handle_checkout(from_num))

    except Exception as e:
        print(f"[Webhook] Error: {e}")

    return "OK", 200


# ── Web dashboard ─────────────────────────────────────────────

@app.route("/")
def dashboard():
    stats = gym_db.get_dashboard_stats()
    return render_template("dashboard.html", stats=stats, gym_name=GYM_NAME)


@app.route("/members")
def members():
    search = request.args.get("q", "").strip()
    rows   = gym_db.get_all_members(search or None)
    today  = date.today().isoformat()
    return render_template("members.html", members=rows, search=search,
                           today=today, gym_name=GYM_NAME)


@app.route("/members/new", methods=["GET", "POST"])
def member_new():
    if request.method == "POST":
        name            = request.form["name"].strip()
        phone           = request.form["phone"].strip()
        membership_type = request.form["membership_type"]
        start_date      = request.form["start_date"]
        expiry_date     = request.form["expiry_date"]
        payment_status  = request.form["payment_status"]
        notes           = request.form.get("notes", "").strip()
        if not (name and phone and start_date and expiry_date):
            flash("Please fill in all required fields.", "danger")
            return redirect(url_for("member_new"))
        try:
            gym_db.add_member(name, phone, membership_type, start_date,
                              expiry_date, payment_status, notes)
            flash(f"Member '{name}' added successfully.", "success")
            return redirect(url_for("members"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
            return redirect(url_for("member_new"))
    return render_template("member_form.html", member=None, action="Add",
                           today=date.today().isoformat(), gym_name=GYM_NAME)


@app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
def member_edit(member_id):
    member = gym_db.get_member(member_id)
    if not member:
        flash("Member not found.", "danger")
        return redirect(url_for("members"))
    if request.method == "POST":
        name            = request.form["name"].strip()
        phone           = request.form["phone"].strip()
        membership_type = request.form["membership_type"]
        start_date      = request.form["start_date"]
        expiry_date     = request.form["expiry_date"]
        payment_status  = request.form["payment_status"]
        notes           = request.form.get("notes", "").strip()
        try:
            gym_db.update_member(member_id, name, phone, membership_type, start_date,
                                 expiry_date, payment_status, notes)
            flash(f"Member '{name}' updated.", "success")
            return redirect(url_for("members"))
        except Exception as e:
            flash(f"Error: {e}", "danger")
    return render_template("member_form.html", member=dict(member), action="Edit",
                           today=date.today().isoformat(), gym_name=GYM_NAME)


@app.route("/members/<int:member_id>/delete", methods=["POST"])
def member_delete(member_id):
    member = gym_db.get_member(member_id)
    if member:
        gym_db.delete_member(member_id)
        flash(f"Member '{member['name']}' deleted.", "success")
    return redirect(url_for("members"))


@app.route("/members/<int:member_id>/pay", methods=["POST"])
def member_pay(member_id):
    member = gym_db.get_member(member_id)
    if not member:
        flash("Member not found.", "danger")
        return redirect(url_for("revenue"))
    amount         = AMOUNT_MAP.get(member["membership_type"], 100.0)
    today          = date.today().isoformat()
    month_paid_for = date.today().strftime("%Y-%m")
    notes          = request.form.get("notes", "").strip()
    gym_db.add_payment(member_id, amount, today, month_paid_for, notes)
    flash(f"Payment of RM{int(amount)} recorded for {member['name']}. ✅", "success")
    next_url = request.form.get("next") or url_for("revenue")
    return redirect(next_url)


# ── Attendance ────────────────────────────────────────────────

@app.route("/attendance")
def attendance():
    filter_date = request.args.get("date", date.today().isoformat())
    rows        = gym_db.get_attendance(filter_date=filter_date)
    all_members = gym_db.get_all_members()
    return render_template("attendance.html", records=rows, filter_date=filter_date,
                           all_members=all_members, gym_name=GYM_NAME)


@app.route("/attendance/checkin", methods=["POST"])
def web_checkin():
    member_id = request.form.get("member_id")
    if member_id:
        member = gym_db.get_member(int(member_id))
        if member:
            ok = gym_db.checkin(int(member_id))
            if ok:
                flash(f"✅ {member['name']} checked in.", "success")
            else:
                flash(f"ℹ️ {member['name']} is already checked in today.", "warning")
        else:
            flash("Member not found.", "danger")
    return redirect(url_for("attendance"))


@app.route("/attendance/checkout", methods=["POST"])
def web_checkout():
    member_id = request.form.get("member_id")
    if member_id:
        member = gym_db.get_member(int(member_id))
        if member:
            ok = gym_db.checkout(int(member_id))
            if ok:
                flash(f"🚪 {member['name']} checked out.", "success")
            else:
                flash(f"ℹ️ {member['name']} has no active check-in today.", "warning")
        else:
            flash("Member not found.", "danger")
    return redirect(url_for("attendance"))


# ── Revenue dashboard ─────────────────────────────────────────

@app.route("/revenue")
def revenue():
    stats = gym_db.get_revenue_stats()
    return render_template("revenue.html", stats=stats, gym_name=GYM_NAME,
                           this_month=date.today().strftime("%B %Y"),
                           today_iso=date.today().isoformat())


@app.route("/scheduler/run-now", methods=["POST"])
def scheduler_run_now():
    _run_daily_jobs()
    flash("Daily reminder jobs executed. WhatsApp messages sent to qualifying members. ✅", "success")
    return redirect(url_for("revenue"))


# ── Health check ──────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "gym": GYM_NAME,
        "scheduler": _scheduler.running,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"{'='*50}")
    print(f"{GYM_NAME} - Record App")
    print(f"Running on http://0.0.0.0:{port}")
    print(f"{'='*50}")
    app.run(host="0.0.0.0", port=port, debug=False)
