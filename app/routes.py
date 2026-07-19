"""Presentation routes, simulated authentication, and session helpers."""

import re
from functools import wraps

from flask import Blueprint, abort, g, jsonify, redirect, render_template, request, session, url_for

from .extensions import db
from .models import User


bp = Blueprint("main", __name__)
DEMO_OTP_CODE = "123456"

DEMO_NOTIFICATIONS = [
    {"id": "missing-jean-bakary", "type": "Missing person", "title": "Jean Bakary, 8", "location": "Yaoundé area · Centre", "time": "2 hours ago", "description": "Jean was last seen near a primary school in Yaoundé. He was wearing a blue school uniform and a red backpack."},
    {"id": "road-douala-a1", "type": "Road accident", "title": "Serious incident on the A1", "location": "Douala · Littoral", "time": "5 hours ago", "description": "A serious road accident was reported near Douala. Nearby people are asked to avoid the area and follow emergency-service instructions."},
    {"id": "patient-yaounde-central", "type": "Unknown patient", "title": "Identification request", "location": "Yaoundé · Cameroon", "time": "Yesterday", "description": "A verified hospital has requested help identifying an unknown patient. Public information is limited to safe identifying details."},
]

INFORMATION_PAGES = {
    "about": ("About SAVE-US", "CEMAC Emergency Network", "A high-trust civic platform dedicated to humanitarian protection and rapid emergency coordination across Central Africa.", [("Our mission", "SAVE-US helps communities structure, review, and responsibly share critical alerts when every second matters."), ("Our role", "We support first-line information gathering and responsible community distribution. We do not replace emergency services or investigative authorities.")]),
    "how-it-works": ("How SAVE-US works", "A safer community alert flow", "Reports are structured, reviewed, and distributed to the right communities.", [("1. Report", "A verified community member or verified hospital submits the information needed for an alert."), ("2. Review", "SAVE-US AI checks completeness, consistency, possible duplicates, and safety rules before publication."), ("3. Reach the right people", "Published alerts are geo-targeted by country, region, and the preferences chosen by each user.")]),
    "partners": ("Partner agencies", "Future collaboration", "SAVE-US is designed to work alongside verified hospitals, civil-society organisations, and public emergency services.", [("For hospitals", "Verified institutions can publish time-sensitive unidentified-patient alerts for their country."), ("For organisations", "Community and humanitarian partners can help extend safe, responsible distribution.")]),
    "support": ("Contact support", "We are here to help", "For account support, safety questions, or help using the demo, contact the SAVE-US team.", [("Safety first", "If someone’s life is in immediate danger, contact local emergency services before using SAVE-US."), ("Demo support", "Support contact channels will be connected in a future MVP iteration.")]),
    "privacy": ("Privacy policy", "Trust & safety", "SAVE-US minimises public exposure of sensitive information while helping communities identify people in distress.", [("Private contact details", "Family phone numbers are not published. Contact actions are routed through controlled sharing options such as WhatsApp."), ("Location safety", "Precise street addresses and GPS coordinates are not shown on public alerts.")]),
    "terms": ("Terms of service", "Responsible use", "SAVE-US users must submit information in good faith and never use the platform to harass, defame, or endanger anyone.", [("Verified reporting", "A verified phone number is required before a citizen can submit a report."), ("No substitute for emergency services", "SAVE-US does not replace police, ambulance, fire, hospital, or other emergency services.")]),
    "data-protection": ("Data protection", "Trust & safety", "Sensitive report information is treated with care and public alerts disclose only what is necessary.", [("Purpose limitation", "Report information is used to structure, review, distribute, and manage emergency alerts."), ("Audit trail", "Reasoned withdrawals, safety reports, and moderation decisions retain a non-public audit record.")]),
    "report-misuse": ("Report misuse", "Trust & safety", "Report false information, privacy concerns, or harmful use so the SAVE-US moderation team can review it.", [("What to report", "Use this channel for incorrect information, a person already found, privacy concerns, or suspected fraudulent use."), ("What happens next", "The report is reviewed by a moderator. Users should never confront or harass another reporter.")]),
}


@bp.before_app_request
def load_current_user() -> None:
    """Load the signed-in user once per request from the Flask session."""
    user_id = session.get("user_id")
    g.current_user = db.session.get(User, user_id) if user_id else None


@bp.app_context_processor
def inject_shared_template_data() -> dict:
    """Expose notification data and real session state to every template."""
    seen_notification_ids = set(session.get("seen_notification_ids", []))
    unread_notification_count = sum(
        item["id"] not in seen_notification_ids for item in DEMO_NOTIFICATIONS
    )
    return {
        "current_user": g.current_user,
        "is_authenticated": g.current_user is not None,
        "notification_items": DEMO_NOTIFICATIONS,
        "notification_count": unread_notification_count,
    }


def login_required(view):
    """Redirect anonymous visitors to phone sign-in before protected pages."""

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.current_user is None:
            session["login_next"] = request.full_path if request.query_string else request.path
            return redirect(url_for("main.sign_in"))
        return view(*args, **kwargs)

    return wrapped_view


def normalise_phone(phone_number: str) -> str:
    """Convert a display phone number into a simple E.164-like value."""
    return re.sub(r"[^\d+]", "", phone_number.strip())


def safe_next_url(next_url: str | None) -> str:
    """Keep post-login redirects within this application."""
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return url_for("main.dashboard")


@bp.get("/")
def home():
    return render_template("home.html")


@bp.route("/sign-in", methods=("GET", "POST"))
def sign_in():
    """Collect a phone number and start the simulated OTP flow."""
    if g.current_user is not None:
        return redirect(url_for("main.dashboard"))

    error = None
    phone_number = ""
    if request.method == "POST":
        phone_number = normalise_phone(request.form.get("phone_number", ""))
        if not re.fullmatch(r"\+\d{8,15}", phone_number):
            error = "Enter a valid phone number, including the country code."
        else:
            session["pending_phone"] = phone_number
            session["pending_otp"] = DEMO_OTP_CODE
            session["otp_attempts"] = 0
            return redirect(url_for("main.verify_otp"))

    return render_template("sign_in.html", active_page=None, app_shell=False, error=error, phone_number=phone_number, demo_otp_code=DEMO_OTP_CODE)


@bp.route("/verify-otp", methods=("GET", "POST"))
def verify_otp():
    """Verify the demo OTP and create a user session for seeded accounts."""
    phone_number = session.get("pending_phone")
    if phone_number is None:
        return redirect(url_for("main.sign_in"))

    error = None
    if request.method == "POST":
        submitted_code = request.form.get("otp_code", "").replace(" ", "")
        if submitted_code != session.get("pending_otp"):
            session["otp_attempts"] = session.get("otp_attempts", 0) + 1
            error = "That verification code is not valid. Try the demo code again."
        else:
            user = db.session.scalar(db.select(User).where(User.phone_number == phone_number))
            session.pop("pending_otp", None)
            session.pop("otp_attempts", None)
            session.pop("pending_phone", None)
            if user is not None:
                session["user_id"] = user.id
                return redirect(safe_next_url(session.pop("login_next", None)))
            session["onboarding_phone"] = phone_number
            return redirect(url_for("main.onboarding_location"))

    return render_template("verify_otp.html", active_page=None, app_shell=False, error=error, phone_number=phone_number, demo_otp_code=DEMO_OTP_CODE)


@bp.get("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", active_page="home", app_shell=True)


@bp.get("/alerts")
@login_required
def alerts():
    return render_template("simple_page.html", title="Active alerts", eyebrow="Cameroon · Centre", description="Browse alerts that match your country, regions, and preferences.", active_page="alerts", app_shell=True, primary_action="Browse alerts")


@bp.get("/alerts/<alert_id>")
@login_required
def alert_detail(alert_id: str):
    alert = next((item for item in DEMO_NOTIFICATIONS if item["id"] == alert_id), None)
    if alert is None:
        abort(404)
    return render_template("alert_detail.html", alert=alert, active_page="alerts", app_shell=True)


@bp.get("/report/missing-person")
@login_required
def report_missing_person():
    return render_template("report_missing_person.html", active_page="report", app_shell=True)


@bp.get("/reports")
@login_required
def my_reports():
    return render_template("simple_page.html", title="My reports", eyebrow="Reporter workspace", description="Manage drafts, active alerts, and reports that need review.", active_page="reports", app_shell=True, primary_action="Report a missing person", primary_url="main.report_missing_person")


@bp.get("/moderator")
@login_required
def moderator_queue():
    return render_template("simple_page.html", title="Moderator queue", eyebrow="Verified moderator access", description="Review reports flagged for possible duplicates, unsafe media, or high fraud risk.", active_page="moderator", app_shell=True, primary_action="View review queue")


@bp.get("/settings")
@login_required
def settings():
    return render_template("simple_page.html", title="Alert preferences", eyebrow="Cameroon · Centre", description="Control the alert categories and regions you want to follow.", active_page="settings", app_shell=True, primary_action="Save preferences")


@bp.get("/onboarding/location")
def onboarding_location():
    return render_template("simple_page.html", title="Where should SAVE-US protect you?", eyebrow="Step 1 of 2 · Location", description="Choose your country and primary region to receive relevant alerts.", active_page=None, app_shell=False, primary_action="Continue")


@bp.get("/notifications")
@login_required
def notifications():
    return render_template("notifications.html", active_page=None, app_shell=True, notifications=DEMO_NOTIFICATIONS)


@bp.post("/notifications/mark-seen")
@login_required
def mark_notifications_seen():
    """Mark the current demo notification set as read in this user session."""
    session["seen_notification_ids"] = [item["id"] for item in DEMO_NOTIFICATIONS]
    return jsonify({"unread_count": 0})


@bp.get("/account")
@login_required
def account():
    return render_template("account.html", active_page="settings", app_shell=True)


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.home"))


@bp.get("/info/<page>")
def information_page(page: str):
    content = INFORMATION_PAGES.get(page)
    if content is None:
        abort(404)
    title, eyebrow, description, sections = content
    return render_template("information_page.html", title=title, eyebrow=eyebrow, description=description, sections=sections)
