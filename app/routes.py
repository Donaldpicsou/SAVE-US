"""Presentation routes for the SAVE-US MVP."""

from flask import Blueprint, abort, redirect, render_template, session, url_for


bp = Blueprint("main", __name__)

DEMO_NOTIFICATIONS = [
    {
        "id": "missing-jean-bakary",
        "type": "Missing person",
        "title": "Jean Bakary, 8",
        "location": "Yaoundé area · Centre",
        "time": "2 hours ago",
        "description": "Jean was last seen near a primary school in Yaoundé. He was wearing a blue school uniform and a red backpack.",
    },
    {
        "id": "road-douala-a1",
        "type": "Road accident",
        "title": "Serious incident on the A1",
        "location": "Douala · Littoral",
        "time": "5 hours ago",
        "description": "A serious road accident was reported near Douala. Nearby people are asked to avoid the area and follow emergency-service instructions.",
    },
    {
        "id": "patient-yaounde-central",
        "type": "Unknown patient",
        "title": "Identification request",
        "location": "Yaoundé · Cameroon",
        "time": "Yesterday",
        "description": "A verified hospital has requested help identifying an unknown patient. Public information is limited to safe identifying details.",
    },
]


@bp.app_context_processor
def inject_notification_preview():
    """Expose temporary notification data to the shared navigation shell."""
    return {
        "notification_items": DEMO_NOTIFICATIONS,
        "notification_count": len(DEMO_NOTIFICATIONS),
    }


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


@bp.get("/")
def home():
    """Render the public SAVE-US landing page."""
    return render_template("home.html")


@bp.get("/sign-in")
def sign_in():
    return render_template(
        "simple_page.html",
        title="Sign in to SAVE-US",
        eyebrow="Secure community access",
        description="Use your verified phone number to access your emergency-alert network.",
        active_page=None,
        app_shell=False,
        primary_action="Send verification code",
    )


@bp.get("/dashboard")
def dashboard():
    return render_template("dashboard.html", active_page="home", app_shell=True)


@bp.get("/alerts")
def alerts():
    return render_template(
        "simple_page.html",
        title="Active alerts",
        eyebrow="Cameroon · Centre",
        description="Browse alerts that match your country, regions, and preferences.",
        active_page="alerts",
        app_shell=True,
        primary_action="Browse alerts",
    )


@bp.get("/alerts/<alert_id>")
def alert_detail(alert_id: str):
    alert = next((item for item in DEMO_NOTIFICATIONS if item["id"] == alert_id), None)
    if alert is None:
        abort(404)
    return render_template("alert_detail.html", alert=alert, active_page="alerts", app_shell=True)


@bp.get("/report/missing-person")
def report_missing_person():
    return render_template("report_missing_person.html", active_page="report", app_shell=True)


@bp.get("/reports")
def my_reports():
    return render_template(
        "simple_page.html",
        title="My reports",
        eyebrow="Reporter workspace",
        description="Manage drafts, active alerts, and reports that need review.",
        active_page="reports",
        app_shell=True,
        primary_action="Report a missing person",
        primary_url="main.report_missing_person",
    )


@bp.get("/moderator")
def moderator_queue():
    return render_template(
        "simple_page.html",
        title="Moderator queue",
        eyebrow="Verified moderator access",
        description="Review reports flagged for possible duplicates, unsafe media, or high fraud risk.",
        active_page="moderator",
        app_shell=True,
        primary_action="View review queue",
    )


@bp.get("/settings")
def settings():
    return render_template(
        "simple_page.html",
        title="Alert preferences",
        eyebrow="Cameroon · Centre",
        description="Control the alert categories and regions you want to follow.",
        active_page="settings",
        app_shell=True,
        primary_action="Save preferences",
    )


@bp.get("/onboarding/location")
def onboarding_location():
    return render_template(
        "simple_page.html",
        title="Where should SAVE-US protect you?",
        eyebrow="Step 1 of 2 · Location",
        description="Choose your country and primary region to receive relevant alerts.",
        active_page=None,
        app_shell=False,
        primary_action="Continue",
    )


@bp.get("/notifications")
def notifications():
    return render_template("notifications.html", active_page=None, app_shell=True, notifications=DEMO_NOTIFICATIONS)


@bp.get("/account")
def account():
    return render_template("account.html", active_page="settings", app_shell=True)


@bp.post("/logout")
def logout():
    """Clear the temporary session and return to the public landing page."""
    session.clear()
    return redirect(url_for("main.home"))


@bp.get("/info/<page>")
def information_page(page: str):
    content = INFORMATION_PAGES.get(page)
    if content is None:
        abort(404)
    title, eyebrow, description, sections = content
    return render_template("information_page.html", title=title, eyebrow=eyebrow, description=description, sections=sections)
