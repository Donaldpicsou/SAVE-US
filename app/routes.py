"""Presentation routes, simulated authentication, and session helpers."""

import re
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, abort, current_app, g, jsonify, redirect, render_template, request, send_file, session, url_for

from .extensions import db
from .ai_service import review_missing_person_alert
from .cemac import load_cemac_data
from .media import PhotoUploadError, delete_private_media, private_media_path, store_missing_person_photo
from .publication import apply_publication_decision, decide_publication
from .targeting import user_receives_alert
from .models import (
    AIReview,
    Alert,
    AlertPreference,
    AlertStatus,
    AlertType,
    MissingPersonDetails,
    MissingPersonSex,
    User,
)


bp = Blueprint("main", __name__)
DEMO_OTP_CODE = "123456"
# CEMAC numbering plans represented as country code -> national-number length.
# The OTP MVP stores a normalised E.164-style value and supports all six members.
CEMAC_PHONE_NUMBER_LENGTHS = {
    "235": 8,  # Chad
    "236": 8,  # Central African Republic
    "237": 9,  # Cameroon
    "240": 9,  # Equatorial Guinea
    "241": 8,  # Gabon
    "242": 9,  # Republic of the Congo
}

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

PREFERENCE_CATEGORIES = (
    {
        "value": AlertType.MISSING_PERSON.value,
        "title": "Missing people",
        "description": "Alerts from your primary and followed regions.",
    },
    {
        "value": AlertType.SUSPECTED_ABDUCTION.value,
        "title": "Suspected abductions",
        "description": "Urgent alerts distributed across your country.",
    },
    {
        "value": AlertType.UNKNOWN_HOSPITAL_PATIENT.value,
        "title": "Unknown hospital patients",
        "description": "Identification requests from verified hospitals in your country.",
    },
    {
        "value": AlertType.ROAD_ACCIDENT.value,
        "title": "Road accidents",
        "description": "Serious road incidents near your primary and followed regions.",
    },
)


ALERT_FEED_FILTERS = (
    ("", "All alerts"),
    (AlertType.MISSING_PERSON.value, "Missing people"),
    (AlertType.SUSPECTED_ABDUCTION.value, "Suspected abductions"),
    (AlertType.UNKNOWN_HOSPITAL_PATIENT.value, "Unknown patients"),
    (AlertType.ROAD_ACCIDENT.value, "Road accidents"),
)


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


def is_valid_cemac_phone(phone_number: str) -> bool:
    """Accept a normalised international number from one of the six CEMAC countries."""
    if not phone_number.startswith("+") or not phone_number[1:].isdigit():
        return False
    return any(
        phone_number.startswith(f"+{country_code}")
        and len(phone_number) == 1 + len(country_code) + national_length
        for country_code, national_length in CEMAC_PHONE_NUMBER_LENGTHS.items()
    )


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
        if not is_valid_cemac_phone(phone_number):
            error = "Enter a valid CEMAC phone number, for example +237 612 345 678 or +241 74 00 11 22."
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
    """Show only published alerts that match the signed-in user's preferences."""
    selected_type = request.args.get("type", "").strip()
    valid_types = {value for value, _label in ALERT_FEED_FILTERS if value}
    if selected_type not in valid_types:
        selected_type = ""
    search = request.args.get("q", "").strip()
    feed_items = targeted_alert_feed(g.current_user, selected_type=selected_type, search=search)
    return render_template(
        "alerts.html",
        active_page="alerts",
        app_shell=True,
        alerts=feed_items,
        filters=ALERT_FEED_FILTERS,
        selected_type=selected_type,
        search=search,
    )


@bp.get("/alerts/<alert_id>")
@login_required
def alert_detail(alert_id: str):
    """Open a public-safe alert only when it belongs in the viewer's feed."""
    stored_alert = db.session.get(Alert, alert_id)
    if stored_alert is not None:
        if not user_receives_alert(g.current_user, stored_alert):
            abort(404)
        return render_template(
            "alert_detail.html",
            alert=public_alert_view(stored_alert),
            back_url=url_for("main.alerts"),
            active_page="alerts",
            app_shell=True,
        )

    # Keep the pre-T19 static notification examples available during the demo.
    alert = next((item for item in DEMO_NOTIFICATIONS if item["id"] == alert_id), None)
    if alert is None:
        abort(404)
    return render_template(
        "alert_detail.html",
        alert=alert,
        back_url=url_for("main.notifications"),
        active_page="alerts",
        app_shell=True,
    )


def targeted_alert_feed(user: User, *, selected_type: str = "", search: str = "") -> list[dict]:
    """Build a sorted, public-safe feed from published alerts eligible for one user."""
    stored_alerts = db.session.scalars(
        db.select(Alert).where(Alert.status == AlertStatus.PUBLISHED)
    ).all()
    search_term = search.casefold()
    matching_alerts = []
    for alert in stored_alerts:
        if not user_receives_alert(user, alert):
            continue
        if selected_type and alert.alert_type.value != selected_type:
            continue
        searchable_text = " ".join((alert.title, alert.public_summary or "")).casefold()
        if search_term and search_term not in searchable_text:
            continue
        matching_alerts.append(alert)
    matching_alerts.sort(key=lambda alert: alert.published_at or alert.created_at, reverse=True)
    return [public_alert_view(alert) for alert in matching_alerts]


def public_alert_view(alert: Alert) -> dict:
    """Return display-only data that never includes private contact or precise location."""
    published_at = alert.published_at or alert.created_at
    location = " · ".join(
        part for part in (alert.approximate_zone, alert.region, alert.country) if part
    )
    initials = "".join(word[0] for word in alert.title.split()[:2]).upper() or "SU"
    return {
        "id": alert.id,
        "title": alert.title,
        "type": alert.alert_type.value.replace("_", " ").title(),
        "type_value": alert.alert_type.value,
        "summary": alert.public_summary or "A SAVE-US alert has been published.",
        "location": location or alert.country,
        "published_label": published_at.strftime("%d %b %Y · %H:%M UTC"),
        "initials": initials,
    }


def owned_missing_person_draft(draft_id: str | None) -> Alert | None:
    """Load a draft only when it belongs to the signed-in reporter."""
    if not draft_id:
        return None
    alert = db.session.get(Alert, draft_id)
    if (
        alert is None
        or alert.reporter_id != g.current_user.id
        or alert.alert_type != AlertType.MISSING_PERSON
        or alert.status != AlertStatus.DRAFT
    ):
        abort(404)
    return alert


def owned_missing_person_alert(alert_id: str) -> Alert:
    """Load a missing-person alert only when it belongs to the signed-in reporter."""
    alert = db.session.get(Alert, alert_id)
    if (
        alert is None
        or alert.reporter_id != g.current_user.id
        or alert.alert_type != AlertType.MISSING_PERSON
    ):
        abort(404)
    return alert


def persist_ai_review(alert: Alert, execution) -> AIReview:
    """Store the validated live or fallback review so the screen can be revisited."""
    review = alert.ai_review
    if review is None:
        review = AIReview(alert=alert)
        db.session.add(review)
    output = execution.output
    review.public_summary = output["public_summary"]
    review.extracted_data = output["extracted_data"]
    review.missing_fields = output["missing_fields"]
    review.duplicate_candidates = output["duplicate_candidates"]
    review.confidence_score = output["confidence_score"]
    review.fraud_risk_score = output["fraud_risk_score"]
    review.decision = output["decision"]
    review.reasons = output["reasons"]
    review.source = execution.source
    review.fallback_reason = execution.fallback_reason
    return review


def parse_missing_person_form() -> tuple[dict[str, object | None], dict[str, str]]:
    """Parse draft-safe fields and return only format errors from the report form."""
    data: dict[str, object | None] = {
        "name": request.form.get("name", "").strip() or None,
        "sex": request.form.get("sex", "").strip() or None,
        "last_seen_location": request.form.get("last_seen_location", "").strip() or None,
        "approximate_zone": request.form.get("approximate_zone", "").strip() or None,
        "clothing_description": request.form.get("clothing_description", "").strip() or None,
        "private_family_contact": request.form.get("private_family_contact", "").strip() or None,
        "circumstances": request.form.get("circumstances", "").strip() or None,
        "age": None,
        "last_seen_at": None,
    }
    errors: dict[str, str] = {}
    raw_age = request.form.get("age", "").strip()
    if raw_age:
        try:
            data["age"] = int(raw_age)
        except ValueError:
            errors["age"] = "Age must be a whole number."

    raw_last_seen_at = request.form.get("last_seen_at", "").strip()
    if raw_last_seen_at:
        try:
            parsed_last_seen_at = datetime.fromisoformat(raw_last_seen_at)
            data["last_seen_at"] = (
                parsed_last_seen_at.replace(tzinfo=timezone.utc)
                if parsed_last_seen_at.tzinfo is None
                else parsed_last_seen_at
            )
        except ValueError:
            errors["last_seen_at"] = "Enter a valid last-seen date and time."

    if data["age"] is not None and not 0 <= data["age"] <= 125:
        errors["age"] = "Age must be between 0 and 125."
    if data["sex"] and data["sex"] not in {item.value for item in MissingPersonSex}:
        errors["sex"] = "Choose a valid sex."
    return data, errors


def report_form_values(details: MissingPersonDetails | None = None) -> dict[str, str]:
    """Supply safe values to repopulate a draft or a failed server validation."""
    if details is None:
        return {field: "" for field in (
            "name", "age", "sex", "last_seen_at", "last_seen_location",
            "approximate_zone", "clothing_description", "private_family_contact", "circumstances",
        )}
    return {
        "name": details.name or "",
        "age": str(details.age) if details.age is not None else "",
        "sex": details.sex or "",
        "last_seen_at": details.last_seen_at.strftime("%Y-%m-%dT%H:%M") if details.last_seen_at else "",
        "last_seen_location": details.last_seen_location or "",
        "approximate_zone": details.alert.approximate_zone or "",
        "clothing_description": details.clothing_description or "",
        "private_family_contact": details.private_family_contact or "",
        "circumstances": details.circumstances or "",
    }


@bp.route("/report/missing-person", methods=("GET", "POST"))
@login_required
def report_missing_person():
    """Create, resume, and validate a missing-person report draft."""
    draft = owned_missing_person_draft(request.values.get("draft_id") or request.args.get("draft"))
    details = draft.missing_person_details if draft else None
    errors: dict[str, str] = {}
    saved = request.args.get("saved") == "1"

    if request.method == "POST":
        form_data, errors = parse_missing_person_form()
        if not errors:
            if draft is None:
                draft = Alert(
                    reporter=g.current_user,
                    alert_type=AlertType.MISSING_PERSON,
                    status=AlertStatus.DRAFT,
                    title=form_data["name"] or "Missing-person report draft",
                    country=g.current_user.country,
                    region=g.current_user.primary_region,
                    approximate_zone=form_data["approximate_zone"],
                )
                details = MissingPersonDetails(alert=draft)
                db.session.add(draft)
            else:
                draft.title = form_data["name"] or "Missing-person report draft"
                draft.approximate_zone = form_data["approximate_zone"]

            for field, value in form_data.items():
                if field != "approximate_zone":
                    setattr(details, field, value)

            action = request.form.get("action", "save_draft")
            selected_photo = request.files.get("photo")
            replaced_photo_path = None
            new_photo_path = None
            if selected_photo and selected_photo.filename:
                try:
                    # Alert ids are generated on flush before their media folder is created.
                    if draft.id is None:
                        db.session.flush()
                    replaced_photo_path = details.photo_path
                    new_photo_path = store_missing_person_photo(
                        selected_photo,
                        upload_root=current_app.config["UPLOAD_FOLDER"],
                        alert_id=draft.id,
                        max_bytes=current_app.config["MAX_PHOTO_UPLOAD_BYTES"],
                    )
                    details.photo_path = new_photo_path
                except PhotoUploadError as error:
                    errors["photo"] = str(error)
            if action == "review":
                errors = {**details.validation_errors(), **errors}

            if action == "review":
                # Preserve the reporter's work even if the server blocks review.
                db.session.commit()
                if new_photo_path:
                    delete_private_media(current_app.config["UPLOAD_FOLDER"], replaced_photo_path)
                if not errors:
                    review = persist_ai_review(draft, review_missing_person_alert(draft))
                    apply_publication_decision(draft, review)
                    db.session.commit()
                    return redirect(url_for("main.report_reviewing", alert_id=draft.id))
            elif not errors:
                db.session.commit()
                if new_photo_path:
                    delete_private_media(current_app.config["UPLOAD_FOLDER"], replaced_photo_path)
                return redirect(url_for("main.report_missing_person", draft=draft.id, saved=1))

    if details is not None:
        values = report_form_values(details)
    elif request.method == "POST":
        values = {key: str(value or "") for key, value in form_data.items()}
        values["last_seen_at"] = request.form.get("last_seen_at", "")
    else:
        values = report_form_values()

    return render_template(
        "report_missing_person.html",
        active_page="report",
        app_shell=True,
        draft=draft,
        values=values,
        errors=errors,
        saved=saved,
    )


@bp.get("/reports/<alert_id>/reviewing")
@login_required
def report_reviewing(alert_id: str):
    """Brief, plain-language transition while a submitted report is checked."""
    alert = owned_missing_person_alert(alert_id)
    if alert.ai_review is None:
        return redirect(url_for("main.report_missing_person", draft=alert.id))
    return render_template(
        "report_reviewing.html",
        active_page="reports",
        app_shell=True,
        alert=alert,
    )


@bp.get("/reports/<alert_id>/ai-review")
@login_required
def ai_review(alert_id: str):
    """Show a reporter the structured, persisted review for their alert."""
    alert = owned_missing_person_alert(alert_id)
    review = alert.ai_review
    if review is None:
        return redirect(url_for("main.report_missing_person", draft=alert.id))
    return render_template(
        "ai_review.html",
        active_page="reports",
        app_shell=True,
        alert=alert,
        review=review,
        publication=decide_publication(review),
    )


@bp.get("/report/missing-person/<alert_id>/photo")
@login_required
def missing_person_photo_preview(alert_id: str):
    """Serve a stored image only to the reporter who owns its draft."""
    draft = owned_missing_person_draft(alert_id)
    details = draft.missing_person_details
    if details is None or not details.photo_path:
        abort(404)
    photo_path = private_media_path(current_app.config["UPLOAD_FOLDER"], details.photo_path)
    if photo_path is None:
        abort(404)
    response = send_file(photo_path, conditional=True, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@bp.get("/reports")
@login_required
def my_reports():
    return render_template("simple_page.html", title="My reports", eyebrow="Reporter workspace", description="Manage drafts, active alerts, and reports that need review.", active_page="reports", app_shell=True, primary_action="Report a missing person", primary_url="main.report_missing_person")


@bp.get("/moderator")
@login_required
def moderator_queue():
    return render_template("simple_page.html", title="Moderator queue", eyebrow="Verified moderator access", description="Review reports flagged for possible duplicates, unsafe media, or high fraud risk.", active_page="moderator", app_shell=True, primary_action="View review queue")


def preference_country_data(user: User) -> tuple[str, dict]:
    """Find the CEMAC dataset entry corresponding to a user's country."""
    dataset = load_cemac_data()
    country_code, country = next(
        (
            (code, data)
            for code, data in dataset.items()
            if data["name"] == user.country
        ),
        ("cameroun", dataset["cameroun"]),
    )
    return country_code, country


def manage_preferences(*, onboarding: bool):
    """Render and persist a user's alert-preference selection."""
    user = g.current_user
    country_code, country = preference_country_data(user)
    preference = user.alert_preference
    enabled_categories = set(preference.enabled_categories) if preference else set()
    followed_regions = set(preference.followed_regions) if preference else set()
    email_enabled = preference.email_notifications_enabled if preference else True
    error = None

    if request.method == "POST":
        enabled_categories = set(request.form.getlist("enabled_categories"))
        followed_regions = set(request.form.getlist("followed_regions"))
        email_enabled = request.form.get("email_notifications_enabled") == "on"
        valid_categories = {category["value"] for category in PREFERENCE_CATEGORIES}
        valid_regions = {item["nom"] for item in country["subdivisions"]}

        if not enabled_categories:
            error = "Choose at least one alert category."
        elif not enabled_categories.issubset(valid_categories):
            error = "One or more alert categories are not supported."
        elif not followed_regions.issubset(valid_regions):
            error = "Choose followed regions from your selected country."
        else:
            if preference is None:
                preference = AlertPreference(user=user)
                db.session.add(preference)
            preference.enabled_categories = sorted(enabled_categories)
            preference.followed_regions = sorted(followed_regions)
            preference.email_notifications_enabled = email_enabled
            db.session.commit()
            return redirect(url_for("main.dashboard"))

    return render_template(
        "preferences.html",
        active_page="settings" if not onboarding else None,
        app_shell=not onboarding,
        onboarding=onboarding,
        country_code=country_code,
        country=country,
        categories=PREFERENCE_CATEGORIES,
        enabled_categories=enabled_categories,
        followed_regions=followed_regions,
        email_enabled=email_enabled,
        error=error,
        primary_region=user.primary_region,
    )


@bp.route("/settings", methods=("GET", "POST"))
@login_required
def settings():
    return manage_preferences(onboarding=False)


@bp.get("/onboarding/location")
@bp.post("/onboarding/location")
def onboarding_location():
    """Save a new or existing user's country and primary region."""
    cemac_data = load_cemac_data()
    pending_phone = session.get("onboarding_phone")
    user = g.current_user

    if user is None and pending_phone is None:
        return redirect(url_for("main.sign_in"))

    selected_country_code = request.form.get("country_code", "")
    selected_region = request.form.get("primary_region", "")
    error = None

    if request.method == "POST":
        country = cemac_data.get(selected_country_code)
        supported_regions = {item["nom"] for item in country["subdivisions"]} if country else set()
        if country is None:
            error = "Choose a supported CEMAC country."
        elif selected_region not in supported_regions:
            error = f"Choose a valid {country['type_subdivision'].lower()} for {country['name']}."
        else:
            if user is None:
                user = User(
                    phone_number=pending_phone,
                    is_phone_verified=True,
                    country=country["name"],
                    primary_region=selected_region,
                )
                db.session.add(user)
                db.session.flush()
                session["user_id"] = user.id
                session.pop("onboarding_phone", None)
            else:
                user.country = country["name"]
                user.primary_region = selected_region

            db.session.commit()
            return redirect(url_for("main.onboarding_preferences"))

    if user is not None:
        selected_country_code = next(
            (code for code, country in cemac_data.items() if country["name"] == user.country),
            "cameroun",
        )
        selected_region = user.primary_region
    elif not selected_country_code:
        selected_country_code = "cameroun"

    return render_template(
        "onboarding_location.html",
        active_page=None,
        app_shell=False,
        cemac_data=cemac_data,
        selected_country_code=selected_country_code,
        selected_region=selected_region,
        error=error,
        is_profile_update=user is not None,
    )


@bp.route("/onboarding/preferences", methods=("GET", "POST"))
@login_required
def onboarding_preferences():
    return manage_preferences(onboarding=True)


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
