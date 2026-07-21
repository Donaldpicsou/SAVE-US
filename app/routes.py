"""Presentation routes, simulated authentication, and session helpers."""

import re
from datetime import datetime, timedelta, timezone
from functools import wraps
from io import BytesIO
from pathlib import Path

from flask import Blueprint, abort, current_app, g, jsonify, redirect, render_template, request, send_file, session, url_for

from .extensions import db
from .administration import configured_safety_rule_values, ensure_default_safety_rules, record_administration_audit
from .alert_sheet_contract import AlertSheetSafetyError, build_alert_sheet
from .alert_sheet_pdf import render_alert_sheet_pdf
from .ai_service import review_missing_person_alert, review_suspected_abduction_alert
from .cemac import load_cemac_data
from .media import PhotoUploadError, delete_private_media, image_metadata, private_media_path, store_alert_photo, store_missing_person_photo
from .notification_service import (
    queue_administrator_request_notifications,
    queue_closure_notifications,
    queue_notification,
    queue_review_outcome_notifications,
)
from .publication import (
    apply_road_accident_publication,
    apply_publication_decision,
    decide_publication,
    expire_due_road_accidents,
)
from .road_media_moderation import (
    MEDIA_STATUS_BLOCKED,
    MEDIA_STATUS_NEEDS_MODERATION,
    review_road_accident_media,
)
from .share_links import build_public_share_message, create_or_get_active_share_link, is_share_link_active, revoke_share_link
from .targeting import eligible_recipients, user_receives_alert
from .models import (
    AdministrationAuditEntry,
    AIReview,
    Alert,
    AlertShareLink,
    AlertPreference,
    AlertStatus,
    AlertType,
    HospitalVerificationRequest,
    HospitalVerificationStatus,
    MissingPersonDetails,
    MissingPersonSex,
    ModeratorAccessRequest,
    ModeratorAccessRequestStatus,
    Notification,
    ReportAction,
    RoadAccidentDetails,
    RoadAccidentMediaReview,
    SAFETY_RULE_SPECS,
    SafetyRule,
    SafetyRuleKey,
    SuspectedAbductionDetails,
    User,
    UserRole,
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

REPORT_STATUS_FILTERS = tuple((status.value, status.value.replace("_", " ").title()) for status in AlertStatus)
REPORT_TYPE_FILTERS = tuple((alert_type.value, alert_type.value.replace("_", " ").title()) for alert_type in AlertType)
REPORTING_OPTIONS = (
    {
        "type": AlertType.MISSING_PERSON,
        "title": "Missing person",
        "description": "Mobilise your region to help locate someone who has disappeared.",
        "icon": "person-search",
        "availability": "available",
    },
    {
        "type": AlertType.SUSPECTED_ABDUCTION,
        "title": "Suspected abduction",
        "description": "Prepare an urgent country-wide report for a suspected kidnapping or abduction.",
        "icon": "warning",
        "availability": "available",
    },
    {
        "type": AlertType.ROAD_ACCIDENT,
        "title": "Road accident",
        "description": "Prepare a rapid local report for a serious collision or road emergency.",
        "icon": "car",
        "availability": "available",
    },
)


@bp.before_app_request
def load_current_user() -> None:
    """Load the signed-in user once per request from the Flask session."""
    # T33 expiry is enforced before building any feed, notification, or report view.
    expire_due_road_accidents()
    user_id = session.get("user_id")
    g.current_user = db.session.get(User, user_id) if user_id else None


@bp.app_context_processor
def inject_shared_template_data() -> dict:
    """Expose a user's notifications and role-appropriate operational-work counters."""
    notification_items = notification_views_for_user(g.current_user, limit=4) if g.current_user else []
    unread_notification_count = (
        db.session.scalar(
            db.select(db.func.count(Notification.id)).where(
                Notification.recipient_id == g.current_user.id,
                Notification.is_read.is_(False),
            )
        )
        if g.current_user
        else 0
    )
    staff_workload = {"moderation_queue": 0, "hospital_requests": 0, "moderator_requests": 0, "administration": 0}
    if g.current_user and g.current_user.role in {UserRole.MODERATOR, UserRole.ADMINISTRATOR}:
        staff_workload["moderation_queue"] = db.session.scalar(
            db.select(db.func.count(Alert.id)).where(Alert.status.in_([AlertStatus.AI_REVIEW, AlertStatus.NEEDS_MODERATION]))
        ) or 0
    if g.current_user and g.current_user.role == UserRole.ADMINISTRATOR:
        staff_workload["hospital_requests"] = db.session.scalar(
            db.select(db.func.count(HospitalVerificationRequest.id)).where(
                HospitalVerificationRequest.status == HospitalVerificationStatus.PENDING
            )
        ) or 0
        staff_workload["moderator_requests"] = db.session.scalar(
            db.select(db.func.count(ModeratorAccessRequest.id)).where(
                ModeratorAccessRequest.status == ModeratorAccessRequestStatus.PENDING
            )
        ) or 0
        staff_workload["administration"] = staff_workload["hospital_requests"] + staff_workload["moderator_requests"]
    return {
        "current_user": g.current_user,
        "is_authenticated": g.current_user is not None,
        "notification_items": notification_items,
        "notification_count": unread_notification_count,
        "staff_workload": staff_workload,
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


def moderator_required(view):
    """Limit the internal moderation queue to designated moderation roles."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.current_user is None:
            return redirect(url_for("main.sign_in", next=request.path))
        if g.current_user.role not in {UserRole.MODERATOR, UserRole.ADMINISTRATOR}:
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view


def administrator_required(view):
    """Reserve administration foundations for the administrator role only."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.current_user is None:
            return redirect(url_for("main.sign_in", next=request.path))
        if g.current_user.role != UserRole.ADMINISTRATOR:
            abort(403)
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
    """Show a compact, live preview of the same preference-targeted alert feed."""
    feed_items = targeted_alert_feed(g.current_user)
    preference = g.current_user.alert_preference
    followed_regions = preference.followed_regions if preference else []
    coverage_regions = list(dict.fromkeys([g.current_user.primary_region, *followed_regions]))
    return render_template(
        "dashboard.html",
        active_page="home",
        app_shell=True,
        recent_alerts=feed_items[:3],
        alert_count=len(feed_items),
        coverage_regions=coverage_regions,
    )


@bp.get("/admin")
@administrator_required
def administrator_home():
    """Provide privacy-minimised operational health metrics for administrators."""
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    pending_statuses = [AlertStatus.AI_REVIEW, AlertStatus.NEEDS_MODERATION]
    active_alerts = db.session.scalar(db.select(db.func.count(Alert.id)).where(Alert.status == AlertStatus.PUBLISHED))
    pending_alerts = db.session.scalar(db.select(db.func.count(Alert.id)).where(Alert.status.in_(pending_statuses)))
    expired_alerts = db.session.scalar(db.select(db.func.count(Alert.id)).where(Alert.status == AlertStatus.EXPIRED))
    reports_created = db.session.scalar(db.select(db.func.count(Alert.id)).where(Alert.created_at >= seven_days_ago))
    pending_hospital_requests = db.session.scalar(
        db.select(db.func.count(HospitalVerificationRequest.id)).where(
            HospitalVerificationRequest.status == HospitalVerificationStatus.PENDING
        )
    )
    pending_moderator_requests = db.session.scalar(
        db.select(db.func.count(ModeratorAccessRequest.id)).where(
            ModeratorAccessRequest.status == ModeratorAccessRequestStatus.PENDING
        )
    )
    moderation_actions = db.session.scalars(
        db.select(ReportAction)
        .where(ReportAction.action.like("moderator_%"), ReportAction.created_at >= seven_days_ago)
        .order_by(ReportAction.created_at.desc())
    ).all()
    action_alert_ids = {action.alert_id for action in moderation_actions}
    action_alerts = db.session.scalars(db.select(Alert).where(Alert.id.in_(action_alert_ids))).all() if action_alert_ids else []
    alerts_by_id = {alert.id: alert for alert in action_alerts}
    moderation_delays = [
        max(0, (action.created_at.timestamp() - alerts_by_id[action.alert_id].created_at.timestamp()) / 3600)
        for action in moderation_actions
        if action.alert_id in alerts_by_id
    ]
    pending_items = db.session.scalars(db.select(Alert).where(Alert.status.in_(pending_statuses))).all()
    pending_ages = [max(0, (now.timestamp() - alert.created_at.timestamp()) / 3600) for alert in pending_items]
    pending_hospital_items = db.session.scalars(
        db.select(HospitalVerificationRequest).where(HospitalVerificationRequest.status == HospitalVerificationStatus.PENDING)
    ).all()
    pending_moderator_items = db.session.scalars(
        db.select(ModeratorAccessRequest).where(ModeratorAccessRequest.status == ModeratorAccessRequestStatus.PENDING)
    ).all()
    pending_administration_items = [*pending_hospital_items, *pending_moderator_items]
    oldest_administration_hours = (
        round(max(0, (now.timestamp() - min(item.created_at for item in pending_administration_items).timestamp()) / 3600), 1)
        if pending_administration_items
        else None
    )
    actor_counts: dict[int, int] = {}
    for action in moderation_actions:
        actor_counts[action.actor_id] = actor_counts.get(action.actor_id, 0) + 1
    moderators = db.session.scalars(db.select(User).where(User.id.in_(set(actor_counts)))).all() if actor_counts else []
    moderator_names = {user.id: user.display_name or f"Account #{user.id}" for user in moderators}
    moderator_activity = [
        {"name": moderator_names.get(actor_id, f"Account #{actor_id}"), "actions": count}
        for actor_id, count in sorted(actor_counts.items(), key=lambda item: (-item[1], item[0]))
    ]
    return render_template(
        "admin_home.html",
        active_page="admin",
        app_shell=True,
        metrics={
            "active_alerts": active_alerts or 0,
            "pending_alerts": pending_alerts or 0,
            "expired_alerts": expired_alerts or 0,
            "reports_created": reports_created or 0,
            "pending_hospital_requests": pending_hospital_requests or 0,
            "pending_moderator_requests": pending_moderator_requests or 0,
            "pending_administration_requests": (pending_hospital_requests or 0) + (pending_moderator_requests or 0),
            "moderation_actions": len(moderation_actions),
            "average_moderation_hours": round(sum(moderation_delays) / len(moderation_delays), 1) if moderation_delays else None,
            "average_pending_hours": round(sum(pending_ages) / len(pending_ages), 1) if pending_ages else None,
            "oldest_administration_hours": oldest_administration_hours,
        },
        moderator_activity=moderator_activity[:6],
    )


def moderator_restore_role(user_id: int) -> UserRole:
    """Restore the role before the latest moderator grant, or citizen by default."""
    grant = db.session.scalar(
        db.select(AdministrationAuditEntry)
        .where(
            AdministrationAuditEntry.target_user_id == user_id,
            AdministrationAuditEntry.action == "moderator_granted",
        )
        .order_by(AdministrationAuditEntry.created_at.desc())
    )
    prior_role = grant.prior_value.get("role") if grant and isinstance(grant.prior_value, dict) else None
    allowed_roles = {
        UserRole.CITIZEN.value: UserRole.CITIZEN,
        UserRole.REPORTER.value: UserRole.REPORTER,
        UserRole.HOSPITAL_REPRESENTATIVE.value: UserRole.HOSPITAL_REPRESENTATIVE,
    }
    return allowed_roles.get(prior_role, UserRole.CITIZEN)


@bp.get("/admin/moderators")
@administrator_required
def administrator_moderators():
    """Find users privately before making an accountable moderator role change."""
    search = request.args.get("q", "").strip()
    query = db.select(User).order_by(User.created_at.desc())
    if search:
        pattern = f"%{search}%"
        query = query.where((User.display_name.ilike(pattern)) | (User.phone_number.ilike(pattern)))
    return render_template(
        "admin_moderators.html",
        active_page="admin",
        app_shell=True,
        users=db.session.scalars(query.limit(50)).all(),
        search=search,
        error=request.args.get("error"),
        message=request.args.get("message"),
    )


@bp.post("/admin/moderators/<int:user_id>/role")
@administrator_required
def update_moderator_role(user_id: int):
    """Grant or remove moderator access with an immutable reasoned audit entry."""
    target = db.session.get(User, user_id)
    if target is None:
        abort(404)
    search = request.form.get("q", "").strip()
    action = request.form.get("action", "").strip()
    reason = request.form.get("reason", "").strip()
    redirect_args = {"q": search} if search else {}

    def rejected(message: str):
        return redirect(url_for("main.administrator_moderators", error=message, **redirect_args))

    if not reason:
        return rejected("A reason is required for every moderator role change.")
    if target.role == UserRole.ADMINISTRATOR:
        administrator_count = db.session.scalar(db.select(db.func.count(User.id)).where(User.role == UserRole.ADMINISTRATOR))
        if administrator_count <= 1:
            return rejected("The last administrator cannot be changed or removed.")
        if target.id == g.current_user.id:
            return rejected("You cannot change your own administrator role from moderator management.")
        return rejected("Administrator roles cannot be changed from moderator management.")
    if target.id == g.current_user.id:
        return rejected("You cannot change your own administrator role from moderator management.")

    prior_value = {"role": target.role.value}
    if action == "grant":
        if target.role == UserRole.MODERATOR:
            return rejected("This user already has moderator access.")
        target.role = UserRole.MODERATOR
        audit_action = "moderator_granted"
    elif action == "revoke":
        if target.role != UserRole.MODERATOR:
            return rejected("Only an active moderator can have moderator access removed.")
        target.role = moderator_restore_role(target.id)
        audit_action = "moderator_revoked"
    else:
        return rejected("Choose whether to grant or remove moderator access.")

    record_administration_audit(
        actor_id=g.current_user.id,
        action=audit_action,
        reason=reason,
        prior_value=prior_value,
        new_value={"role": target.role.value},
        target_user_id=target.id,
    )
    db.session.commit()
    return redirect(url_for("main.administrator_moderators", message="Moderator access updated.", **redirect_args))


@bp.route("/moderator-access/request", methods=("GET", "POST"))
@login_required
def request_moderator_access():
    """Allow a verified non-staff user to request, but never self-grant, moderator access."""
    if g.current_user.role in {UserRole.MODERATOR, UserRole.ADMINISTRATOR}:
        abort(403)
    existing_request = db.session.scalar(
        db.select(ModeratorAccessRequest).where(
            ModeratorAccessRequest.submitted_by_id == g.current_user.id,
            ModeratorAccessRequest.status == ModeratorAccessRequestStatus.PENDING,
        )
    )
    reason = request.form.get("reason", "").strip()
    errors: dict[str, str] = {}
    submitted = request.args.get("submitted") == "1"
    if request.method == "POST":
        if existing_request is not None:
            errors["request"] = "A moderator-access request is already awaiting review."
        else:
            access_request = ModeratorAccessRequest(submitted_by_id=g.current_user.id, reason=reason)
            errors = access_request.submission_validation_errors()
            if not errors:
                db.session.add(access_request)
                db.session.flush()
                queue_administrator_request_notifications(
                    request_type="moderator_access",
                    request_id=access_request.id,
                    title="Moderator access request awaiting review",
                    body="A verified SAVE-US user requested moderator access. Open the private request to review the stated reason.",
                )
                db.session.commit()
                return redirect(url_for("main.request_moderator_access", submitted="1"))
    return render_template(
        "moderator_access_request.html",
        active_page="settings",
        app_shell=True,
        existing_request=existing_request,
        submitted=submitted,
        reason=reason,
        errors=errors,
    )


@bp.get("/admin/moderator-requests")
@administrator_required
def administrator_moderator_requests():
    """List private, pending-or-decided moderator-access requests for administrators."""
    selected_status = request.args.get("status", ModeratorAccessRequestStatus.PENDING.value)
    statuses = {status.value: status for status in ModeratorAccessRequestStatus}
    if selected_status not in statuses and selected_status != "all":
        selected_status = ModeratorAccessRequestStatus.PENDING.value
    statement = db.select(ModeratorAccessRequest).order_by(ModeratorAccessRequest.created_at.desc())
    if selected_status != "all":
        statement = statement.where(ModeratorAccessRequest.status == statuses[selected_status])
    return render_template(
        "admin_moderator_requests.html",
        active_page="admin",
        app_shell=True,
        access_requests=db.session.scalars(statement).all(),
        selected_status=selected_status,
    )


def private_moderator_access_request(request_id: str) -> ModeratorAccessRequest:
    """Resolve one moderator-access request only in the administrator workspace."""
    access_request = db.session.get(ModeratorAccessRequest, request_id)
    if access_request is None:
        abort(404)
    return access_request


@bp.get("/admin/moderator-requests/<request_id>")
@administrator_required
def administrator_moderator_request_detail(request_id: str):
    """Display a private moderator-access request and its decision form."""
    return render_template(
        "admin_moderator_request_detail.html",
        active_page="admin",
        app_shell=True,
        access_request=private_moderator_access_request(request_id),
        error=request.args.get("error"),
    )


@bp.post("/admin/moderator-requests/<request_id>/decision")
@administrator_required
def decide_moderator_access_request(request_id: str):
    """Approve or reject one requested role with an immutable, reasoned audit record."""
    access_request = private_moderator_access_request(request_id)
    if access_request.status != ModeratorAccessRequestStatus.PENDING:
        abort(409)
    decision = request.form.get("decision", "").strip()
    reason = request.form.get("reason", "").strip()
    if decision not in {"approve", "reject"} or not reason:
        return redirect(url_for("main.administrator_moderator_request_detail", request_id=request_id, error="Choose approve or reject and provide a decision reason."))

    applicant = access_request.submitted_by
    prior_value = {"status": access_request.status.value, "role": applicant.role.value}
    access_request.reviewed_by_id = g.current_user.id
    access_request.reviewed_at = datetime.now(timezone.utc)
    access_request.decision_reason = reason
    if decision == "approve":
        access_request.status = ModeratorAccessRequestStatus.APPROVED
        applicant.role = UserRole.MODERATOR
        audit_action = "moderator_access_request_approved"
        reporter_title = "Your moderator access was approved"
        reporter_body = "SAVE-US approved your moderator-access request. Your account can now open the moderator queue."
    else:
        access_request.status = ModeratorAccessRequestStatus.REJECTED
        audit_action = "moderator_access_request_rejected"
        reporter_title = "Your moderator access request was not approved"
        reporter_body = "SAVE-US recorded a decision on your moderator-access request. Open this notification for the next steps."
    validation_errors = access_request.decision_validation_errors()
    if validation_errors:
        return redirect(url_for("main.administrator_moderator_request_detail", request_id=request_id, error=next(iter(validation_errors.values()))))
    record_administration_audit(
        actor_id=g.current_user.id,
        action=audit_action,
        reason=reason,
        prior_value=prior_value,
        new_value={"status": access_request.status.value, "role": applicant.role.value},
        target_user_id=applicant.id,
        moderator_access_request_id=access_request.id,
    )
    queue_notification(
        applicant,
        alert=None,
        kind="moderator_access_request_decision",
        title=reporter_title,
        body=reporter_body,
        public_location="Account",
    )
    db.session.commit()
    return redirect(url_for("main.administrator_moderator_requests", message="Moderator-access request decision recorded."))


@bp.route("/admin/safety-rules", methods=("GET", "POST"))
@administrator_required
def administrator_safety_rules():
    """Edit only bounded future-facing safety thresholds with a reasoned audit."""
    rules = ensure_default_safety_rules()
    if request.method == "POST":
        reason = request.form.get("reason", "").strip()
        proposed: dict[SafetyRuleKey, int] = {}
        errors: list[str] = []
        for rule in rules:
            raw_value = request.form.get(f"rule_{rule.key.value}", "").strip()
            try:
                value = int(raw_value)
            except ValueError:
                errors.append(f"{rule.key.value.replace('_', ' ')} must be a whole number.")
                continue
            specification = SAFETY_RULE_SPECS[rule.key]
            if not specification["minimum"] <= value <= specification["maximum"]:
                errors.append(
                    f"{rule.key.value.replace('_', ' ')} must be between {specification['minimum']} and {specification['maximum']}."
                )
            else:
                proposed[rule.key] = value
        changed_rules = [rule for rule in rules if proposed.get(rule.key) != rule.value]
        if changed_rules and not reason:
            errors.append("A reason is required for every safety-rule change.")
        if errors:
            return render_template(
                "admin_safety_rules.html",
                active_page="admin",
                app_shell=True,
                rules=rules,
                specifications=SAFETY_RULE_SPECS,
                error=" ".join(errors),
            )
        for rule in changed_rules:
            prior_value = {"key": rule.key.value, "value": rule.value}
            rule.value = proposed[rule.key]
            record_administration_audit(
                actor_id=g.current_user.id,
                action="safety_rule_updated",
                reason=reason,
                prior_value=prior_value,
                new_value={"key": rule.key.value, "value": rule.value},
            )
        db.session.commit()
        message = "Safety rules saved. They apply to future decisions only." if changed_rules else "No safety-rule values changed."
        return redirect(url_for("main.administrator_safety_rules", message=message))
    db.session.commit()  # persist missing safe defaults for newly initialised local databases.
    return render_template(
        "admin_safety_rules.html",
        active_page="admin",
        app_shell=True,
        rules=rules,
        specifications=SAFETY_RULE_SPECS,
        message=request.args.get("message"),
    )


@bp.get("/admin/audit-log")
@administrator_required
def administrator_audit_log():
    """Show a privacy-minimised, administrator-only record of staff actions."""
    actor_id = request.args.get("actor", "").strip()
    selected_action = request.args.get("action", "").strip()
    subject = request.args.get("subject", "").strip().lower()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    error = None
    try:
        start = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
        # Use the next day as an exclusive bound, retaining all times on date_to.
        end = datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999) if date_to else None
    except ValueError:
        start = end = None
        error = "Use YYYY-MM-DD for audit dates."

    admin_query = db.select(AdministrationAuditEntry).order_by(AdministrationAuditEntry.created_at.desc()).limit(200)
    moderation_query = (
        db.select(ReportAction)
        .where(ReportAction.action.like("moderator_%"))
        .order_by(ReportAction.created_at.desc())
        .limit(200)
    )
    if actor_id.isdigit():
        admin_query = admin_query.where(AdministrationAuditEntry.actor_id == int(actor_id))
        moderation_query = moderation_query.where(ReportAction.actor_id == int(actor_id))
    if start:
        admin_query = admin_query.where(AdministrationAuditEntry.created_at >= start)
        moderation_query = moderation_query.where(ReportAction.created_at >= start)
    if end:
        admin_query = admin_query.where(AdministrationAuditEntry.created_at <= end)
        moderation_query = moderation_query.where(ReportAction.created_at <= end)

    administration_entries = db.session.scalars(admin_query).all()
    moderation_entries = db.session.scalars(moderation_query).all()
    actor_ids = {entry.actor_id for entry in administration_entries} | {entry.actor_id for entry in moderation_entries}
    target_ids = {entry.target_user_id for entry in administration_entries if entry.target_user_id}
    users = db.session.scalars(db.select(User).where(User.id.in_(actor_ids | target_ids))).all() if actor_ids or target_ids else []
    users_by_id = {user.id: user for user in users}
    alert_ids = {entry.alert_id for entry in administration_entries if entry.alert_id} | {entry.alert_id for entry in moderation_entries}
    alerts = db.session.scalars(db.select(Alert).where(Alert.id.in_(alert_ids))).all() if alert_ids else []
    alerts_by_id = {alert.id: alert for alert in alerts}

    def account_label(user_id: int | None) -> str:
        user = users_by_id.get(user_id) if user_id else None
        return user.display_name if user and user.display_name else f"Account #{user_id}" if user_id else "Removed account"

    records = []
    for entry in administration_entries:
        if entry.target_user_id:
            target = f"Account #{entry.target_user_id}"
            subject_terms = f"{target} {account_label(entry.target_user_id)}"
        elif entry.alert_id:
            alert = alerts_by_id.get(entry.alert_id)
            target = f"Report #{entry.alert_id[:8]}"
            subject_terms = f"{target} {entry.alert_id} {alert.title if alert else ''}"
        elif entry.hospital_verification_request_id:
            target = f"Institution request #{entry.hospital_verification_request_id[:8]}"
            subject_terms = f"{target} {entry.hospital_verification_request_id}"
        else:
            target, subject_terms = "Platform setting", "platform setting"
        records.append({
            "created_at": entry.created_at,
            "actor": account_label(entry.actor_id),
            "actor_terms": f"{account_label(entry.actor_id)} {users_by_id.get(entry.actor_id).phone_number if entry.actor_id in users_by_id else ''}",
            "action": entry.action,
            "source": "Administration",
            "target": target,
            "reason": entry.reason,
            "subject_terms": subject_terms,
        })
    for entry in moderation_entries:
        alert = alerts_by_id.get(entry.alert_id)
        records.append({
            "created_at": entry.created_at,
            "actor": account_label(entry.actor_id),
            "actor_terms": f"{account_label(entry.actor_id)} {users_by_id.get(entry.actor_id).phone_number if entry.actor_id in users_by_id else ''}",
            "action": entry.action,
            "source": "Moderation",
            "target": f"Report #{entry.alert_id[:8]}",
            "reason": entry.reason,
            "subject_terms": f"{entry.alert_id} {alert.title if alert else ''}",
        })
    available_actions = sorted({entry.action for entry in administration_entries} | {entry.action for entry in moderation_entries})
    if selected_action:
        records = [record for record in records if record["action"] == selected_action]
    if subject:
        records = [record for record in records if subject in record["subject_terms"].lower()]
    records.sort(key=lambda record: record["created_at"], reverse=True)
    staff = db.session.scalars(
        db.select(User).where(User.role.in_([UserRole.ADMINISTRATOR, UserRole.MODERATOR])).order_by(User.display_name, User.id)
    ).all()
    return render_template(
        "admin_audit_log.html",
        active_page="admin",
        app_shell=True,
        records=records,
        staff=staff,
        actions=available_actions,
        filters={"actor": actor_id, "action": selected_action, "subject": request.args.get("subject", ""), "from": date_from, "to": date_to},
        error=error,
    )


@bp.route("/hospital-verification/request", methods=("GET", "POST"))
@login_required
def request_hospital_verification():
    """Let a verified community account submit one private institution request."""
    if g.current_user.role in {
        UserRole.HOSPITAL_REPRESENTATIVE,
        UserRole.MODERATOR,
        UserRole.ADMINISTRATOR,
    }:
        abort(403)
    existing_request = db.session.scalar(
        db.select(HospitalVerificationRequest).where(
            HospitalVerificationRequest.submitted_by_id == g.current_user.id,
            HospitalVerificationRequest.status == HospitalVerificationStatus.PENDING,
        )
    )
    form_values = {
        "hospital_name": request.form.get("hospital_name", "").strip(),
        "contact_name": request.form.get("contact_name", g.current_user.display_name or "").strip(),
        "contact_phone": request.form.get("contact_phone", g.current_user.phone_number).strip(),
        "supporting_document_reference": request.form.get("supporting_document_reference", "").strip(),
    }
    errors: dict[str, str] = {}
    submitted = request.args.get("submitted") == "1"
    if request.method == "POST":
        if existing_request is not None:
            errors["request"] = "A hospital-verification request is already awaiting review."
        else:
            contact_phone = normalise_phone(form_values["contact_phone"])
            verification_request = HospitalVerificationRequest(
                submitted_by_id=g.current_user.id,
                hospital_name=form_values["hospital_name"],
                country=g.current_user.country,
                region=g.current_user.primary_region,
                contact_name=form_values["contact_name"],
                contact_phone=contact_phone,
                supporting_document_reference=form_values["supporting_document_reference"],
            )
            errors = verification_request.submission_validation_errors()
            if contact_phone and not is_valid_cemac_phone(contact_phone):
                errors["contact_phone"] = "Enter a valid CEMAC institution contact phone number."
            if not errors:
                db.session.add(verification_request)
                db.session.flush()
                queue_administrator_request_notifications(
                    request_type="hospital_verification",
                    request_id=verification_request.id,
                    title="Hospital verification awaiting review",
                    body="A verified SAVE-US user submitted a private institution-verification request. Open the private request to review its evidence reference.",
                )
                db.session.commit()
                return redirect(url_for("main.request_hospital_verification", submitted="1"))
    return render_template(
        "hospital_verification_request.html",
        active_page="settings",
        app_shell=True,
        form_values=form_values,
        errors=errors,
        existing_request=existing_request,
        submitted=submitted,
    )


@bp.get("/admin/hospital-verifications")
@administrator_required
def administrator_hospital_verifications():
    """List private institutional-verification requests for an administrator."""
    selected_status = request.args.get("status", HospitalVerificationStatus.PENDING.value)
    statuses = {status.value: status for status in HospitalVerificationStatus}
    if selected_status not in statuses and selected_status != "all":
        selected_status = HospitalVerificationStatus.PENDING.value
    query = db.select(HospitalVerificationRequest).order_by(HospitalVerificationRequest.created_at.desc())
    if selected_status != "all":
        query = query.where(HospitalVerificationRequest.status == statuses[selected_status])
    verification_requests = db.session.scalars(query).all()
    return render_template(
        "admin_hospital_verifications.html",
        active_page="admin",
        app_shell=True,
        verification_requests=verification_requests,
        selected_status=selected_status,
        statuses=HospitalVerificationStatus,
    )


def private_hospital_verification_request(request_id: str) -> HospitalVerificationRequest:
    """Resolve one request only for the administrator-only verification workflow."""
    verification_request = db.session.get(HospitalVerificationRequest, request_id)
    if verification_request is None:
        abort(404)
    return verification_request


@bp.get("/admin/hospital-verifications/<request_id>")
@administrator_required
def administrator_hospital_verification_detail(request_id: str):
    """Display the private evidence reference and decision history for one request."""
    verification_request = private_hospital_verification_request(request_id)
    return render_template(
        "admin_hospital_verification_detail.html",
        active_page="admin",
        app_shell=True,
        verification_request=verification_request,
        error=request.args.get("error"),
    )


@bp.post("/admin/hospital-verifications/<request_id>/decision")
@administrator_required
def decide_hospital_verification(request_id: str):
    """Approve or reject once, with a mandatory private reason and audit entry."""
    verification_request = private_hospital_verification_request(request_id)
    if verification_request.status != HospitalVerificationStatus.PENDING:
        abort(409)
    decision = request.form.get("decision", "").strip()
    reason = request.form.get("reason", "").strip()
    if decision not in {"approve", "reject"} or not reason:
        return redirect(
            url_for(
                "main.administrator_hospital_verification_detail",
                request_id=request_id,
                error="Choose approve or reject and provide a decision reason.",
            )
        )

    applicant = verification_request.submitted_by
    prior_value = {"status": verification_request.status.value, "role": applicant.role.value}
    verification_request.reviewed_by_id = g.current_user.id
    verification_request.reviewed_at = datetime.now(timezone.utc)
    verification_request.decision_reason = reason
    if decision == "approve":
        verification_request.status = HospitalVerificationStatus.APPROVED
        applicant.role = UserRole.HOSPITAL_REPRESENTATIVE
        action = "hospital_verification_approved"
    else:
        verification_request.status = HospitalVerificationStatus.REJECTED
        action = "hospital_verification_rejected"
    validation_errors = verification_request.decision_validation_errors()
    if validation_errors:
        return redirect(
            url_for(
                "main.administrator_hospital_verification_detail",
                request_id=request_id,
                error=next(iter(validation_errors.values())),
            )
        )
    record_administration_audit(
        actor_id=g.current_user.id,
        action=action,
        reason=reason,
        prior_value=prior_value,
        new_value={"status": verification_request.status.value, "role": applicant.role.value},
        target_user_id=applicant.id,
        hospital_verification_request_id=verification_request.id,
    )
    db.session.commit()
    return redirect(url_for("main.administrator_hospital_verifications", status="all"))


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
        if stored_alert.reporter_id != g.current_user.id and not user_receives_alert(g.current_user, stored_alert):
            abort(404)
        return render_template(
            "alert_detail.html",
            alert=public_alert_view(stored_alert),
            back_url=url_for("main.alerts"),
            active_page="alerts",
            app_shell=True,
        )

    abort(404)


def may_access_alert(user: User, alert: Alert) -> bool:
    """Return whether a signed-in user may access an alert's safe public view."""
    return (
        alert.reporter_id == user.id
        or user.role in {UserRole.MODERATOR, UserRole.ADMINISTRATOR}
        or user_receives_alert(user, alert)
    )


@bp.get("/alerts/<alert_id>/sheet")
@login_required
def alert_sheet(alert_id: str):
    """Render an authorised A4-friendly sheet from the T49 public-safe contract."""
    stored_alert = db.session.get(Alert, alert_id)
    if stored_alert is None or not may_access_alert(g.current_user, stored_alert):
        abort(404)
    try:
        sheet = build_alert_sheet(stored_alert, generated_at=datetime.now(timezone.utc))
    except AlertSheetSafetyError:
        # Do not generate a printable or externally shareable representation
        # when a public field fails the contract's data-minimisation checks.
        abort(404)
    return render_template(
        "alert_sheet.html",
        sheet=sheet,
        generated_at=datetime.now(timezone.utc),
    )


@bp.get("/alerts/<alert_id>/sheet.pdf")
@login_required
def alert_sheet_pdf(alert_id: str):
    """Download a private, non-cacheable PDF generated from the T49 contract."""
    stored_alert = db.session.get(Alert, alert_id)
    if stored_alert is None or not may_access_alert(g.current_user, stored_alert):
        abort(404)
    try:
        generated_at = datetime.now(timezone.utc)
        sheet = build_alert_sheet(stored_alert, generated_at=generated_at)
        logo_path = Path(current_app.static_folder) / "images" / "save-us-logo.png"
        pdf = render_alert_sheet_pdf(sheet, generated_at=generated_at, logo_path=logo_path)
    except AlertSheetSafetyError:
        abort(404)
    category_name = stored_alert.alert_type.value.replace("_", "-")
    filename = f"save-us-{category_name}-alert-{stored_alert.id[:8]}.pdf"
    response = send_file(
        BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.post("/alerts/<alert_id>/share-links")
@login_required
def create_alert_share_link(alert_id: str):
    """Issue or reuse an opaque external link for an authorised published alert.

    This is deliberately a JSON endpoint. T53 will attach it to visible
    copy/Web Share/WhatsApp controls without exposing report identifiers.
    """
    stored_alert = db.session.get(Alert, alert_id)
    if stored_alert is None or not may_access_alert(g.current_user, stored_alert):
        abort(404)
    try:
        # Validate the same T49 representation before any public URL exists.
        sheet = build_alert_sheet(stored_alert, generated_at=datetime.now(timezone.utc))
        link = create_or_get_active_share_link(stored_alert, created_by_id=g.current_user.id)
    except (AlertSheetSafetyError, ValueError):
        abort(404)
    public_url = url_for("main.public_share_link", token=link.token, _external=True)
    share_text = build_public_share_message(sheet, public_url=public_url)
    return jsonify(
        {
            "url": public_url,
            "expires_at": link.expires_at.isoformat(),
            "share_title": "SAVE-US Emergency Alert",
            "share_text": share_text,
            "whatsapp_text": share_text,
        }
    )


@bp.post("/alerts/<alert_id>/share-links/<link_id>/revoke")
@login_required
def revoke_alert_share_link(alert_id: str, link_id: str):
    """Revoke a link while retaining its non-public accountability record."""
    stored_alert = db.session.get(Alert, alert_id)
    link = db.session.get(AlertShareLink, link_id)
    if stored_alert is None or link is None or link.alert_id != stored_alert.id:
        abort(404)
    if stored_alert.reporter_id != g.current_user.id and g.current_user.role not in {
        UserRole.MODERATOR,
        UserRole.ADMINISTRATOR,
    }:
        abort(404)
    revoke_share_link(link)
    return ("", 204)


@bp.get("/s/<token>")
def public_share_link(token: str):
    """Serve only the T49-safe external representation for a live opaque link."""
    link = db.session.scalar(db.select(AlertShareLink).where(AlertShareLink.token == token))
    if link is None or not is_share_link_active(link):
        abort(404)
    try:
        generated_at = datetime.now(timezone.utc)
        sheet = build_alert_sheet(link.alert, generated_at=generated_at)
    except AlertSheetSafetyError:
        abort(404)
    response = current_app.make_response(
        render_template("shared_alert.html", sheet=sheet, generated_at=generated_at)
    )
    # Tokens may be forwarded; do not let browsers, proxies, or referrers
    # retain them beyond the intentional recipient.
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@bp.get("/alerts/<alert_id>/photo")
@login_required
def alert_photo(alert_id: str):
    """Serve a validated report photo to its owner or an eligible alert recipient."""
    alert = db.session.get(Alert, alert_id)
    if alert is None or (
        alert.reporter_id != g.current_user.id
        and g.current_user.role not in {UserRole.MODERATOR, UserRole.ADMINISTRATOR}
        and not user_receives_alert(g.current_user, alert)
    ):
        abort(404)
    details = alert.missing_person_details or alert.suspected_abduction_details
    photo_path = details.photo_path if details is not None else (
        alert.road_accident_details.media_references[0]
        if alert.road_accident_details and alert.road_accident_details.media_references
        else None
    )
    if not photo_path:
        abort(404)
    resolved_photo_path = private_media_path(current_app.config["UPLOAD_FOLDER"], photo_path)
    if resolved_photo_path is None:
        abort(404)
    response = send_file(resolved_photo_path, conditional=True, max_age=0)
    # The original remains private: browsers must not cache or share a public URL.
    response.headers["Cache-Control"] = "private, no-store"
    return response


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
    category_presentation = {
        AlertType.MISSING_PERSON: {
            "coverage_label": f"Regional community search · {alert.region or alert.country}",
            "safety_label": "Share verified information only",
            "safety_note": "Do not publish private family contact details or precise locations.",
            "primary_action_label": "Contact family on WhatsApp",
        },
        AlertType.SUSPECTED_ABDUCTION: {
            "coverage_label": f"Country-wide urgent alert · {alert.country}",
            "safety_label": "Do not confront anyone involved",
            "safety_note": "Share verified facts only. Do not attempt an intervention or publish private contact details.",
            "primary_action_label": "Share urgent alert",
        },
        AlertType.ROAD_ACCIDENT: {
            "coverage_label": f"Regional road-safety alert · {alert.region or alert.country}",
            "safety_label": "Avoid the affected area and drive carefully",
            "safety_note": "The location shown is approximate. Precise coordinates and uploaded media remain protected.",
            "primary_action_label": "Share road alert",
        },
    }.get(alert.alert_type, {})
    expires_label = None
    if alert.alert_type == AlertType.ROAD_ACCIDENT and alert.expires_at:
        expires_label = alert.expires_at.strftime("Expires %d %b %Y · %H:%M UTC")
    return {
        "id": alert.id,
        "title": alert.title,
        "type": alert.alert_type.value.replace("_", " ").title(),
        "type_value": alert.alert_type.value,
        "summary": alert.public_summary or "A SAVE-US alert has been published.",
        "location": location or alert.country,
        "published_label": published_at.strftime("%d %b %Y · %H:%M UTC"),
        "initials": initials,
        "coverage_label": category_presentation.get("coverage_label", "Targeted SAVE-US alert"),
        "safety_label": category_presentation.get("safety_label", "Share responsibly"),
        "safety_note": category_presentation.get("safety_note", "SAVE-US does not display private contact details or precise locations publicly."),
        "primary_action_label": category_presentation.get("primary_action_label", "Share alert"),
        "expires_label": expires_label,
        # Uploaded photos stay protected; published abduction and missing-person alerts may expose them to eligible users.
        "photo_url": (
            url_for("main.alert_photo", alert_id=alert.id)
            if (alert.missing_person_details and alert.missing_person_details.photo_path)
            or (alert.suspected_abduction_details and alert.suspected_abduction_details.photo_path)
            or (alert.road_accident_details and alert.road_accident_details.media_references)
            else None
        ),
    }


def notification_views_for_user(user: User, *, limit: int | None = None, filter_name: str = "all") -> list[dict]:
    """Build private, public-safe notification display data for one recipient."""
    statement = db.select(Notification).where(Notification.recipient_id == user.id)
    if filter_name == "unread":
        statement = statement.where(Notification.is_read.is_(False))
    elif filter_name == "read":
        statement = statement.where(Notification.is_read.is_(True))
    statement = statement.order_by(Notification.created_at.desc())
    if limit is not None:
        statement = statement.limit(limit)
    return [notification_view(notification) for notification in db.session.scalars(statement).all()]


def notification_view(notification: Notification) -> dict:
    """Return a notification without private contact data or inaccessible media."""
    alert = notification.alert
    photo_available = (
        alert is not None
        and notification.kind in {"alert_published", "report_published", "report_needs_moderation"}
        and (
            (alert.missing_person_details is not None and bool(alert.missing_person_details.photo_path))
            or (alert.suspected_abduction_details is not None and bool(alert.suspected_abduction_details.photo_path))
            or (alert.road_accident_details is not None and bool(alert.road_accident_details.media_references))
        )
    )
    return {
        "id": notification.id,
        "kind": notification.kind,
        "title": notification.title,
        "body": notification.body,
        "location": notification.public_location or "SAVE-US",
        "created_label": notification.created_at.strftime("%d %b %Y · %H:%M UTC"),
        "is_read": notification.is_read,
        "email_delivery_status": notification.email_delivery_status,
        "type_value": alert.alert_type.value if alert else "report_update",
        "is_administrative": notification.kind == "administrative_request",
        "photo_url": url_for("main.alert_photo", alert_id=alert.id) if photo_available else None,
        "open_url": url_for("main.open_notification", notification_id=notification.id),
    }


def owned_notification(notification_id: str) -> Notification:
    """Load one persisted notification only for its intended recipient."""
    notification = db.session.get(Notification, notification_id)
    if notification is None or notification.recipient_id != g.current_user.id:
        abort(404)
    return notification


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


def owned_suspected_abduction_draft(draft_id: str | None) -> Alert | None:
    """Load an abduction draft only for its reporter and never through another form."""
    if not draft_id:
        return None
    alert = db.session.get(Alert, draft_id)
    if (
        alert is None
        or alert.reporter_id != g.current_user.id
        or alert.alert_type != AlertType.SUSPECTED_ABDUCTION
        or alert.status != AlertStatus.DRAFT
    ):
        abort(404)
    return alert


def owned_suspected_abduction_alert(alert_id: str) -> Alert:
    """Load one reporter-owned suspected-abduction alert."""
    alert = db.session.get(Alert, alert_id)
    if (
        alert is None
        or alert.reporter_id != g.current_user.id
        or alert.alert_type != AlertType.SUSPECTED_ABDUCTION
    ):
        abort(404)
    return alert


def owned_road_accident_draft(draft_id: str | None) -> Alert | None:
    """Load a road-accident draft only for the reporter who owns it."""
    if not draft_id:
        return None
    alert = db.session.get(Alert, draft_id)
    if (
        alert is None
        or alert.reporter_id != g.current_user.id
        or alert.alert_type != AlertType.ROAD_ACCIDENT
        or alert.status != AlertStatus.DRAFT
    ):
        abort(404)
    return alert


def owned_road_accident_alert(alert_id: str) -> Alert:
    """Load one reporter-owned road-accident alert without crossing incident types."""
    alert = db.session.get(Alert, alert_id)
    if (
        alert is None
        or alert.reporter_id != g.current_user.id
        or alert.alert_type != AlertType.ROAD_ACCIDENT
    ):
        abort(404)
    return alert


def owned_report_alert(alert_id: str) -> Alert:
    """Load any report only when it belongs to the signed-in reporting user."""
    alert = db.session.get(Alert, alert_id)
    if alert is None or alert.reporter_id != g.current_user.id:
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


def persist_road_accident_media_review(alert: Alert, result) -> RoadAccidentMediaReview:
    """Store the private media-safety outcome and apply its safe lifecycle state."""
    review = alert.road_accident_media_review
    if review is None:
        review = RoadAccidentMediaReview(alert=alert)
        db.session.add(review)
    review.media_reference = result.media_reference
    review.status = result.status
    review.reason = result.reason
    review.source = result.source
    if result.status == MEDIA_STATUS_BLOCKED:
        alert.status = AlertStatus.REJECTED
    elif result.status == MEDIA_STATUS_NEEDS_MODERATION:
        alert.status = AlertStatus.NEEDS_MODERATION
    else:
        # T33 remains responsible for the later publication decision and expiry.
        alert.status = AlertStatus.AI_REVIEW
    return review


def parse_missing_person_form() -> tuple[dict[str, object | None], dict[str, str]]:
    """Parse draft-safe fields and return only format errors from the report form."""
    _countries, regions_by_country = incident_location_reference()
    selected_country = request.form.get("country", "").strip() or g.current_user.country
    selected_region = request.form.get("region", "").strip() or g.current_user.primary_region
    data: dict[str, object | None] = {
        "country": selected_country,
        "region": selected_region,
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
    if selected_country not in regions_by_country:
        errors["country"] = "Choose a supported CEMAC country."
    elif selected_region not in regions_by_country[selected_country]:
        errors["region"] = "Choose a region from the selected country."
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


def parse_suspected_abduction_form() -> tuple[dict[str, object | None], dict[str, str]]:
    """Parse abduction-only draft data and validate the selected incident location."""
    _countries, regions_by_country = incident_location_reference()
    selected_country = request.form.get("country", "").strip() or g.current_user.country
    selected_region = request.form.get("region", "").strip() or g.current_user.primary_region
    data: dict[str, object | None] = {
        "title": request.form.get("title", "").strip() or None,
        "country": selected_country,
        "region": selected_region,
        "approximate_zone": request.form.get("approximate_zone", "").strip() or None,
        "description": request.form.get("description", "").strip() or None,
        "circumstances": request.form.get("circumstances", "").strip() or None,
        "private_contact": request.form.get("private_contact", "").strip() or None,
        "abduction_at": None,
    }
    errors: dict[str, str] = {}
    if selected_country not in regions_by_country:
        errors["country"] = "Choose a supported CEMAC country."
    elif selected_region not in regions_by_country[selected_country]:
        errors["region"] = "Choose a region from the selected country."

    raw_abduction_at = request.form.get("abduction_at", "").strip()
    if raw_abduction_at:
        try:
            parsed_abduction_at = datetime.fromisoformat(raw_abduction_at)
            data["abduction_at"] = (
                parsed_abduction_at.replace(tzinfo=timezone.utc)
                if parsed_abduction_at.tzinfo is None
                else parsed_abduction_at
            )
        except ValueError:
            errors["abduction_at"] = "Enter a valid incident date and time."
    return data, errors


def parse_road_accident_form() -> tuple[dict[str, object | None], dict[str, str]]:
    """Parse road-accident draft data, retaining a manual location fallback for GPS."""
    _countries, regions_by_country = incident_location_reference()
    selected_country = request.form.get("country", "").strip() or g.current_user.country
    selected_region = request.form.get("region", "").strip() or g.current_user.primary_region
    data: dict[str, object | None] = {
        "title": request.form.get("title", "").strip() or None,
        "country": selected_country,
        "region": selected_region,
        "approximate_zone": request.form.get("approximate_zone", "").strip() or None,
        "manual_location": request.form.get("manual_location", "").strip() or None,
        "affected_region": selected_region,
        "immediate_needs": request.form.get("immediate_needs", "").strip() or None,
        "description": request.form.get("description", "").strip() or None,
        "occurred_at": None,
        "latitude": None,
        "longitude": None,
        "victim_count": None,
    }
    errors: dict[str, str] = {}
    if selected_country not in regions_by_country:
        errors["country"] = "Choose a supported CEMAC country."
    elif selected_region not in regions_by_country[selected_country]:
        errors["region"] = "Choose a region from the selected country."

    raw_occurred_at = request.form.get("occurred_at", "").strip()
    if raw_occurred_at:
        try:
            parsed_occurred_at = datetime.fromisoformat(raw_occurred_at)
            data["occurred_at"] = parsed_occurred_at.replace(tzinfo=timezone.utc) if parsed_occurred_at.tzinfo is None else parsed_occurred_at
        except ValueError:
            errors["occurred_at"] = "Enter a valid accident date and time."

    raw_victim_count = request.form.get("victim_count", "").strip()
    if raw_victim_count:
        try:
            data["victim_count"] = int(raw_victim_count)
        except ValueError:
            errors["victim_count"] = "Victim count must be a whole number."

    raw_latitude = request.form.get("latitude", "").strip()
    raw_longitude = request.form.get("longitude", "").strip()
    if bool(raw_latitude) != bool(raw_longitude):
        errors["coordinates"] = "Latitude and longitude must be provided together."
    elif raw_latitude and raw_longitude:
        try:
            data["latitude"] = float(raw_latitude)
            data["longitude"] = float(raw_longitude)
        except ValueError:
            errors["coordinates"] = "Enter valid latitude and longitude values."
    return data, errors


def incident_location_reference() -> tuple[list[str], dict[str, list[str]]]:
    """Return public CEMAC countries and their selectable subdivisions by display name."""
    dataset = load_cemac_data()
    regions_by_country = {
        country["name"]: [subdivision["nom"] for subdivision in country["subdivisions"]]
        for country in dataset.values()
    }
    return sorted(regions_by_country), regions_by_country


def report_form_values(
    details: MissingPersonDetails | None = None,
    *,
    default_country: str = "",
    default_region: str = "",
) -> dict[str, str]:
    """Supply safe values to repopulate a draft or a failed server validation."""
    if details is None:
        values = {field: "" for field in (
            "name", "age", "sex", "last_seen_at", "last_seen_location",
            "approximate_zone", "clothing_description", "private_family_contact", "circumstances",
        )}
        values["country"] = default_country
        values["region"] = default_region
        return values
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
        "country": details.alert.country or default_country,
        "region": details.alert.region or default_region,
    }


def abduction_form_values(
    details: SuspectedAbductionDetails | None = None,
    *,
    default_country: str = "",
    default_region: str = "",
) -> dict[str, str]:
    """Return safe values for a new or resumed suspected-abduction draft."""
    if details is None:
        return {
            "title": "",
            "country": default_country,
            "region": default_region,
            "approximate_zone": "",
            "abduction_at": "",
            "description": "",
            "circumstances": "",
            "private_contact": "",
        }
    return {
        "title": details.alert.title or "",
        "country": details.alert.country or default_country,
        "region": details.alert.region or default_region,
        "approximate_zone": details.alert.approximate_zone or "",
        "abduction_at": details.abduction_at.strftime("%Y-%m-%dT%H:%M") if details.abduction_at else "",
        "description": details.description or "",
        "circumstances": details.circumstances or "",
        "private_contact": details.private_contact or "",
    }


def road_accident_form_values(
    details: RoadAccidentDetails | None = None,
    *,
    default_country: str = "",
    default_region: str = "",
) -> dict[str, str]:
    """Return safe values for a new or resumed road-accident draft."""
    if details is None:
        return {
            "title": "", "country": default_country, "region": default_region,
            "approximate_zone": "", "manual_location": "", "occurred_at": "",
            "latitude": "", "longitude": "", "victim_count": "", "immediate_needs": "", "description": "",
        }
    return {
        "title": details.alert.title or "",
        "country": details.alert.country or default_country,
        "region": details.alert.region or default_region,
        "approximate_zone": details.alert.approximate_zone or "",
        "manual_location": details.manual_location or "",
        "occurred_at": details.occurred_at.strftime("%Y-%m-%dT%H:%M") if details.occurred_at else "",
        "latitude": str(details.latitude) if details.latitude is not None else "",
        "longitude": str(details.longitude) if details.longitude is not None else "",
        "victim_count": str(details.victim_count) if details.victim_count is not None else "",
        "immediate_needs": details.immediate_needs or "",
        "description": details.description or "",
    }


@bp.get("/report")
@login_required
def report_incident():
    """Offer one verified-user entry point without creating cross-type drafts."""
    selected_type = request.args.get("type", "").strip()
    valid_types = {option["type"].value for option in REPORTING_OPTIONS}
    if selected_type not in valid_types:
        selected_type = ""
    return render_template(
        "report_incident.html",
        active_page="report",
        app_shell=True,
        reporting_options=REPORTING_OPTIONS,
        selected_type=selected_type,
    )


@bp.route("/report/suspected-abduction", methods=("GET", "POST"))
@bp.route("/report/suspected_abduction", methods=("GET", "POST"))
@login_required
def report_suspected_abduction():
    """Create, resume, and submit a category-isolated suspected-abduction draft."""
    draft = owned_suspected_abduction_draft(request.values.get("draft_id") or request.args.get("draft"))
    details = draft.suspected_abduction_details if draft else None
    errors: dict[str, str] = {}
    saved = request.args.get("saved") == "1"

    if request.method == "POST":
        form_data, errors = parse_suspected_abduction_form()
        if not errors:
            created_draft = False
            if draft is None:
                created_draft = True
                draft = Alert(
                    reporter=g.current_user,
                    alert_type=AlertType.SUSPECTED_ABDUCTION,
                    status=AlertStatus.DRAFT,
                    title=form_data["title"] or "Suspected-abduction report draft",
                    country=form_data["country"],
                    region=form_data["region"],
                    approximate_zone=form_data["approximate_zone"],
                )
                details = SuspectedAbductionDetails(alert=draft)
                db.session.add(draft)
            else:
                draft.title = form_data["title"] or "Suspected-abduction report draft"
                draft.country = form_data["country"]
                draft.region = form_data["region"]
                draft.approximate_zone = form_data["approximate_zone"]

            for field, value in form_data.items():
                if field not in {"title", "country", "region", "approximate_zone"}:
                    setattr(details, field, value)

            action = request.form.get("action", "save_draft")
            selected_photo = request.files.get("photo")
            replaced_photo_path = None
            new_photo_path = None
            if selected_photo and selected_photo.filename:
                try:
                    # Reject invalid evidence before this new draft is flushed to storage.
                    image_metadata(
                        selected_photo,
                        max_bytes=current_app.config["MAX_PHOTO_UPLOAD_BYTES"],
                    )
                    if draft.id is None:
                        db.session.flush()
                    replaced_photo_path = details.photo_path
                    new_photo_path = store_alert_photo(
                        selected_photo,
                        upload_root=current_app.config["UPLOAD_FOLDER"],
                        alert_id=draft.id,
                        category="suspected_abduction",
                        max_bytes=current_app.config["MAX_PHOTO_UPLOAD_BYTES"],
                    )
                    details.photo_path = new_photo_path
                except PhotoUploadError as error:
                    errors["photo"] = str(error)
                    if created_draft:
                        # A failed optional upload must not leave a new draft behind.
                        db.session.rollback()
                        draft = None
                        details = None

            if action == "submit" and details is not None:
                if not form_data["title"]:
                    errors["title"] = "A short report title is required."
                errors = {**details.validation_errors(), **errors}
                if not errors:
                    draft.status = AlertStatus.AI_REVIEW

            if action == "submit":
                # Keep valid draft data when a required field still needs correction.
                db.session.commit()
                if new_photo_path:
                    delete_private_media(current_app.config["UPLOAD_FOLDER"], replaced_photo_path)
                if not errors:
                    review = persist_ai_review(draft, review_suspected_abduction_alert(draft))
                    apply_publication_decision(draft, review, safety_rules=configured_safety_rule_values())
                    queue_review_outcome_notifications(draft)
                    db.session.commit()
                    return redirect(url_for("main.abduction_report_submitted", alert_id=draft.id))
            elif not errors:
                db.session.commit()
                if new_photo_path:
                    delete_private_media(current_app.config["UPLOAD_FOLDER"], replaced_photo_path)
                return redirect(url_for("main.report_suspected_abduction", draft=draft.id, saved=1))

    if details is not None:
        values = abduction_form_values(
            details,
            default_country=g.current_user.country,
            default_region=g.current_user.primary_region,
        )
    elif request.method == "POST":
        values = {key: str(value or "") for key, value in form_data.items()}
        values["abduction_at"] = request.form.get("abduction_at", "")
    else:
        values = abduction_form_values(
            default_country=g.current_user.country,
            default_region=g.current_user.primary_region,
        )

    incident_countries, regions_by_country = incident_location_reference()
    return render_template(
        "report_suspected_abduction.html",
        active_page="report",
        app_shell=True,
        draft=draft,
        values=values,
        errors=errors,
        saved=saved,
        incident_countries=incident_countries,
        regions_by_country=regions_by_country,
    )


@bp.route("/report/road-accident", methods=("GET", "POST"))
@bp.route("/report/road_accident", methods=("GET", "POST"))
@login_required
def report_road_accident():
    """Create and resume a rapid road-accident draft with optional private media."""
    draft = owned_road_accident_draft(request.values.get("draft_id") or request.args.get("draft"))
    details = draft.road_accident_details if draft else None
    errors: dict[str, str] = {}
    saved = request.args.get("saved") == "1"

    if request.method == "POST":
        form_data, errors = parse_road_accident_form()
        if not errors:
            created_draft = False
            if draft is None:
                created_draft = True
                draft = Alert(
                    reporter=g.current_user,
                    alert_type=AlertType.ROAD_ACCIDENT,
                    status=AlertStatus.DRAFT,
                    title=form_data["title"] or "Road-accident report draft",
                    country=form_data["country"],
                    region=form_data["region"],
                    approximate_zone=form_data["approximate_zone"],
                )
                details = RoadAccidentDetails(alert=draft, media_references=[])
                db.session.add(draft)
            else:
                draft.title = form_data["title"] or "Road-accident report draft"
                draft.country = form_data["country"]
                draft.region = form_data["region"]
                draft.approximate_zone = form_data["approximate_zone"]

            for field, value in form_data.items():
                if field not in {"title", "country", "region", "approximate_zone"}:
                    setattr(details, field, value)

            action = request.form.get("action", "save_draft")
            selected_photo = request.files.get("photo")
            replaced_media_references = list(details.media_references or [])
            new_photo_path = None
            if selected_photo and selected_photo.filename:
                try:
                    image_metadata(selected_photo, max_bytes=current_app.config["MAX_PHOTO_UPLOAD_BYTES"])
                    if draft.id is None:
                        db.session.flush()
                    new_photo_path = store_alert_photo(
                        selected_photo,
                        upload_root=current_app.config["UPLOAD_FOLDER"],
                        alert_id=draft.id,
                        category="road_accident",
                        max_bytes=current_app.config["MAX_PHOTO_UPLOAD_BYTES"],
                    )
                    # T31 intentionally supports one optional image; later media work can extend this list safely.
                    details.media_references = [new_photo_path]
                except PhotoUploadError as error:
                    errors["photo"] = str(error)
                    if created_draft:
                        db.session.rollback()
                        draft = None
                        details = None

            if action == "submit" and details is not None:
                if not form_data["title"]:
                    errors["title"] = "A short report title is required."
                if not form_data["approximate_zone"]:
                    errors["approximate_zone"] = "An approximate public area is required."
                errors = {**details.validation_errors(), **errors}
                if not errors:
                    # T32/T33 perform media moderation and publication. T31 only queues the complete report.
                    draft.status = AlertStatus.AI_REVIEW

            if action == "submit":
                if not errors:
                    persist_road_accident_media_review(
                        draft,
                        review_road_accident_media(
                            draft,
                            upload_root=current_app.config["UPLOAD_FOLDER"],
                            max_bytes=current_app.config["MAX_PHOTO_UPLOAD_BYTES"],
                            api_key=current_app.config.get("OPENAI_API_KEY"),
                            model=current_app.config["OPENAI_MEDIA_MODEL"],
                            timeout=current_app.config["OPENAI_TIMEOUT_SECONDS"],
                        ),
                    )
                    apply_road_accident_publication(draft, safety_rules=configured_safety_rule_values())
                    if draft.status in {AlertStatus.PUBLISHED, AlertStatus.NEEDS_MODERATION}:
                        queue_review_outcome_notifications(draft)
                db.session.commit()
                if new_photo_path:
                    for old_path in replaced_media_references:
                        delete_private_media(current_app.config["UPLOAD_FOLDER"], old_path)
                if not errors:
                    return redirect(url_for("main.road_accident_report_submitted", alert_id=draft.id))
            elif not errors:
                db.session.commit()
                if new_photo_path:
                    for old_path in replaced_media_references:
                        delete_private_media(current_app.config["UPLOAD_FOLDER"], old_path)
                return redirect(url_for("main.report_road_accident", draft=draft.id, saved=1))

    if details is not None:
        values = road_accident_form_values(details, default_country=g.current_user.country, default_region=g.current_user.primary_region)
    elif request.method == "POST":
        values = {key: str(value or "") for key, value in form_data.items()}
        values["occurred_at"] = request.form.get("occurred_at", "")
    else:
        values = road_accident_form_values(default_country=g.current_user.country, default_region=g.current_user.primary_region)

    incident_countries, regions_by_country = incident_location_reference()
    return render_template(
        "report_road_accident.html",
        active_page="report",
        app_shell=True,
        draft=draft,
        values=values,
        errors=errors,
        saved=saved,
        incident_countries=incident_countries,
        regions_by_country=regions_by_country,
    )


@bp.get("/reports/<alert_id>/submitted")
@login_required
def abduction_report_submitted(alert_id: str):
    """Confirm the review outcome without exposing internal implementation details."""
    alert = owned_suspected_abduction_alert(alert_id)
    if alert.status == AlertStatus.DRAFT:
        return redirect(url_for("main.report_suspected_abduction", draft=alert.id))
    return render_template("report_submitted.html", active_page="reports", app_shell=True, alert=alert)


@bp.get("/reports/road-accident/<alert_id>/submitted")
@login_required
def road_accident_report_submitted(alert_id: str):
    """Show the plain-language confirmation for a queued road-accident report."""
    alert = owned_road_accident_alert(alert_id)
    if alert.status == AlertStatus.DRAFT:
        return redirect(url_for("main.report_road_accident", draft=alert.id))
    return render_template("report_submitted.html", active_page="reports", app_shell=True, alert=alert)


@bp.get("/report/suspected-abduction/<alert_id>/photo")
@login_required
def suspected_abduction_photo_preview(alert_id: str):
    """Serve an abduction-draft image only to its reporting owner."""
    draft = owned_suspected_abduction_draft(alert_id)
    details = draft.suspected_abduction_details
    if details is None or not details.photo_path:
        abort(404)
    photo_path = private_media_path(current_app.config["UPLOAD_FOLDER"], details.photo_path)
    if photo_path is None:
        abort(404)
    response = send_file(photo_path, conditional=True, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@bp.get("/report/road-accident/<alert_id>/photo")
@login_required
def road_accident_photo_preview(alert_id: str):
    """Serve one stored road-accident draft image only to its reporting owner."""
    draft = owned_road_accident_draft(alert_id)
    details = draft.road_accident_details
    photo_path = details.media_references[0] if details and details.media_references else None
    resolved_path = private_media_path(current_app.config["UPLOAD_FOLDER"], photo_path) if photo_path else None
    if resolved_path is None:
        abort(404)
    response = send_file(resolved_path, conditional=True, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@bp.get("/report/<incident_type>")
@login_required
def incident_report_unavailable(incident_type: str):
    """Keep future category routes separate until their dedicated forms exist."""
    unavailable_types = {}
    title = unavailable_types.get(incident_type)
    if title is None:
        abort(404)
    return render_template(
        "incident_report_unavailable.html",
        active_page="report",
        app_shell=True,
        incident_title=title,
        incident_type=incident_type,
    )


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
                    country=form_data["country"],
                    region=form_data["region"],
                    approximate_zone=form_data["approximate_zone"],
                )
                details = MissingPersonDetails(alert=draft)
                db.session.add(draft)
            else:
                draft.title = form_data["name"] or "Missing-person report draft"
                draft.country = form_data["country"]
                draft.region = form_data["region"]
                draft.approximate_zone = form_data["approximate_zone"]

            for field, value in form_data.items():
                if field not in {"approximate_zone", "country", "region"}:
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
                    apply_publication_decision(draft, review, safety_rules=configured_safety_rule_values())
                    queue_review_outcome_notifications(draft)
                    db.session.commit()
                    return redirect(url_for("main.report_reviewing", alert_id=draft.id))
            elif not errors:
                db.session.commit()
                if new_photo_path:
                    delete_private_media(current_app.config["UPLOAD_FOLDER"], replaced_photo_path)
                return redirect(url_for("main.report_missing_person", draft=draft.id, saved=1))

    if details is not None:
        values = report_form_values(
            details,
            default_country=g.current_user.country,
            default_region=g.current_user.primary_region,
        )
    elif request.method == "POST":
        values = {key: str(value or "") for key, value in form_data.items()}
        values["last_seen_at"] = request.form.get("last_seen_at", "")
    else:
        values = report_form_values(
            default_country=g.current_user.country,
            default_region=g.current_user.primary_region,
        )

    incident_countries, regions_by_country = incident_location_reference()

    return render_template(
        "report_missing_person.html",
        active_page="report",
        app_shell=True,
        draft=draft,
        values=values,
        errors=errors,
        saved=saved,
        incident_countries=incident_countries,
        regions_by_country=regions_by_country,
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
        publication=decide_publication(
            review,
            minimum_confidence=configured_safety_rule_values()[SafetyRuleKey.MINIMUM_PUBLICATION_CONFIDENCE],
            maximum_fraud_risk=configured_safety_rule_values()[SafetyRuleKey.MAXIMUM_PUBLICATION_FRAUD_RISK],
        ),
    )


@bp.get("/reports/suspected-abduction/<alert_id>/ai-review")
@login_required
def suspected_abduction_ai_review(alert_id: str):
    """Show the reporting owner the persisted suspected-abduction review."""
    alert = owned_suspected_abduction_alert(alert_id)
    review = alert.ai_review
    if review is None:
        return redirect(url_for("main.report_suspected_abduction", draft=alert.id))
    return render_template(
        "ai_review.html",
        active_page="reports",
        app_shell=True,
        alert=alert,
        review=review,
        publication=decide_publication(
            review,
            minimum_confidence=configured_safety_rule_values()[SafetyRuleKey.MINIMUM_PUBLICATION_CONFIDENCE],
            maximum_fraud_risk=configured_safety_rule_values()[SafetyRuleKey.MAXIMUM_PUBLICATION_FRAUD_RISK],
        ),
        report_form_url=url_for("main.report_suspected_abduction", draft=alert.id),
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
    """List and filter the signed-in reporter's private report workspace."""
    selected_status = request.args.get("status", "").strip()
    selected_type = request.args.get("type", "").strip()
    search = request.args.get("q", "").strip()
    valid_statuses = {value for value, _label in REPORT_STATUS_FILTERS}
    valid_types = {value for value, _label in REPORT_TYPE_FILTERS}
    if selected_status not in valid_statuses:
        selected_status = ""
    if selected_type not in valid_types:
        selected_type = ""

    reports = db.session.scalars(
        db.select(Alert).where(Alert.reporter_id == g.current_user.id)
    ).all()
    search_term = search.casefold()
    reports = [
        report for report in reports
        if (not selected_status or report.status.value == selected_status)
        and (not selected_type or report.alert_type.value == selected_type)
        and (not search_term or search_term in " ".join((report.title, report.public_summary or "")).casefold())
    ]
    reports.sort(key=lambda report: report.updated_at or report.created_at, reverse=True)
    return render_template(
        "my_reports.html",
        active_page="reports",
        app_shell=True,
        reports=reports,
        report_status_filters=REPORT_STATUS_FILTERS,
        report_type_filters=REPORT_TYPE_FILTERS,
        selected_status=selected_status,
        selected_type=selected_type,
        search=search,
        action_error=request.args.get("action_error"),
    )


@bp.post("/reports/<alert_id>/close")
@login_required
def close_report(alert_id: str):
    """Mark one owned report as found or withdrawn and preserve a reasoned audit record."""
    alert = owned_report_alert(alert_id)
    action = request.form.get("action", "").strip()
    reason = request.form.get("reason", "").strip()
    if alert.alert_type == AlertType.ROAD_ACCIDENT:
        allowed_actions = {"closed"}
    elif alert.alert_type == AlertType.MISSING_PERSON:
        allowed_actions = {"reported_found", "withdrawn"}
    else:
        abort(400)
    if action not in allowed_actions:
        abort(400)
    if not reason:
        return redirect(url_for("main.my_reports", action_error="Provide a reason before closing a report."))
    if alert.status in {AlertStatus.REPORTED_FOUND, AlertStatus.WITHDRAWN, AlertStatus.EXPIRED}:
        return redirect(url_for("main.my_reports", action_error="This report has already been closed."))

    former_recipients = []
    if alert.status == AlertStatus.PUBLISHED:
        users = db.session.scalars(db.select(User).where(User.is_phone_verified.is_(True))).all()
        former_recipients = eligible_recipients(alert, users)
    alert.status = AlertStatus.REPORTED_FOUND if action == "reported_found" else AlertStatus.WITHDRAWN
    db.session.add(ReportAction(alert=alert, actor_id=g.current_user.id, action=action, reason=reason))
    if alert.alert_type == AlertType.ROAD_ACCIDENT:
        # The audit action is "closed" while recipients use the existing safe withdrawal message.
        queue_closure_notifications(alert, former_recipients, action="withdrawn")
    else:
        queue_closure_notifications(alert, former_recipients, action=action)
    db.session.commit()
    return redirect(url_for("main.my_reports"))


@bp.get("/moderator")
@moderator_required
def moderator_queue():
    """Show moderation candidates plus published abductions for post-publication review."""
    alerts = db.session.scalars(
        db.select(Alert)
        .where(
            (Alert.status == AlertStatus.NEEDS_MODERATION)
            | ((Alert.alert_type == AlertType.SUSPECTED_ABDUCTION) & (Alert.status == AlertStatus.PUBLISHED))
        )
        .order_by(Alert.updated_at.desc())
    ).all()
    return render_template(
        "moderator_queue.html",
        active_page="moderator",
        app_shell=True,
        alerts=alerts,
    )


def moderator_reviewable_alert(alert_id: str) -> Alert:
    """Load a report that is awaiting moderation or an abduction kept for safety review."""
    alert = db.session.get(Alert, alert_id)
    if alert is None:
        abort(404)
    if alert.status == AlertStatus.NEEDS_MODERATION:
        return alert
    if alert.alert_type == AlertType.SUSPECTED_ABDUCTION and alert.status == AlertStatus.PUBLISHED:
        return alert
    abort(404)


def moderator_private_details(alert: Alert) -> list[tuple[str, str]]:
    """Return only the private data needed for an accountable human decision."""
    if alert.alert_type == AlertType.MISSING_PERSON and alert.missing_person_details:
        details = alert.missing_person_details
        return [
            ("Name", details.name or "Not provided"),
            ("Age", str(details.age) if details.age is not None else "Not provided"),
            ("Sex", details.sex or "Not provided"),
            ("Last seen", details.last_seen_at.strftime("%d %b %Y · %H:%M UTC") if details.last_seen_at else "Not provided"),
            ("Private last-seen location", details.last_seen_location or "Not provided"),
            ("Private family contact", details.private_family_contact or "Not provided"),
            ("Clothing", details.clothing_description or "Not provided"),
            ("Circumstances", details.circumstances or "Not provided"),
        ]
    if alert.alert_type == AlertType.SUSPECTED_ABDUCTION and alert.suspected_abduction_details:
        details = alert.suspected_abduction_details
        return [
            ("Reported time", details.abduction_at.strftime("%d %b %Y · %H:%M UTC") if details.abduction_at else "Not provided"),
            ("Description", details.description or "Not provided"),
            ("Circumstances", details.circumstances or "Not provided"),
            ("Private contact", details.private_contact or "Not provided"),
        ]
    if alert.alert_type == AlertType.ROAD_ACCIDENT and alert.road_accident_details:
        details = alert.road_accident_details
        coordinates = f"{details.latitude}, {details.longitude}" if details.latitude is not None and details.longitude is not None else "Not provided"
        return [
            ("Occurred at", details.occurred_at.strftime("%d %b %Y · %H:%M UTC") if details.occurred_at else "Not provided"),
            ("Manual location", details.manual_location or "Not provided"),
            ("Coordinates", coordinates),
            ("Victim count", str(details.victim_count) if details.victim_count is not None else "Not provided"),
            ("Immediate needs", details.immediate_needs or "Not provided"),
            ("Description", details.description or "Not provided"),
        ]
    return [("Report data", "No category-specific details are available.")]


def queue_moderation_update(alert: Alert, *, title: str, message: str) -> None:
    """Notify the reporter of a human decision without exposing internal moderation data."""
    queue_notification(
        alert.reporter,
        alert=alert,
        kind="moderation_update",
        title=title,
        body=message,
        public_location=" · ".join(part for part in (alert.approximate_zone, alert.region, alert.country) if part),
    )


@bp.get("/moderator/alerts/<alert_id>")
@moderator_required
def moderator_review_alert(alert_id: str):
    """Show restricted report information and AI/media signals for human review."""
    alert = moderator_reviewable_alert(alert_id)
    photo_available = bool(
        (alert.missing_person_details and alert.missing_person_details.photo_path)
        or (alert.suspected_abduction_details and alert.suspected_abduction_details.photo_path)
        or (alert.road_accident_details and alert.road_accident_details.media_references)
    )
    return render_template(
        "moderator_review.html",
        active_page="moderator",
        app_shell=True,
        alert=alert,
        private_details=moderator_private_details(alert),
        photo_url=url_for("main.alert_photo", alert_id=alert.id) if photo_available else None,
        media_review=alert.road_accident_media_review,
    )


@bp.post("/moderator/alerts/<alert_id>/decision")
@moderator_required
def moderate_alert(alert_id: str):
    """Apply a reasoned human decision and preserve a non-public audit entry."""
    alert = moderator_reviewable_alert(alert_id)
    decision = request.form.get("decision", "").strip()
    reason = request.form.get("reason", "").strip()
    allowed_decisions = {"publish", "request_information", "reject"}
    if alert.alert_type == AlertType.SUSPECTED_ABDUCTION and alert.status == AlertStatus.PUBLISHED:
        allowed_decisions = {"withdraw"}
    if decision not in allowed_decisions:
        abort(400)
    if not reason:
        return redirect(url_for("main.moderator_review_alert", alert_id=alert.id, error="A decision reason is required."))

    if decision == "publish":
        if alert.alert_type == AlertType.ROAD_ACCIDENT:
            media_review = alert.road_accident_media_review
            if media_review is None or media_review.status == MEDIA_STATUS_BLOCKED:
                return redirect(url_for("main.moderator_review_alert", alert_id=alert.id, error="A blocked or missing media review cannot be approved."))
            media_review.status = "clear"
            media_review.reason = f"Human moderator approved this media. {reason}"
            media_review.source = "human_moderator"
            publication = apply_road_accident_publication(alert, safety_rules=configured_safety_rule_values())
            if not publication.is_published:
                return redirect(url_for("main.moderator_review_alert", alert_id=alert.id, error=publication.reason))
        else:
            if alert.ai_review is None or not alert.ai_review.public_summary:
                return redirect(url_for("main.moderator_review_alert", alert_id=alert.id, error="A validated AI review is required before human publication."))
            alert.status = AlertStatus.PUBLISHED
            alert.published_at = datetime.now(timezone.utc)
            alert.public_summary = alert.ai_review.public_summary
        db.session.add(ReportAction(alert=alert, actor_id=g.current_user.id, action="moderator_publish", reason=reason))
        queue_review_outcome_notifications(alert)
    elif decision == "request_information":
        alert.status = AlertStatus.NEEDS_MODERATION
        db.session.add(ReportAction(alert=alert, actor_id=g.current_user.id, action="moderator_request_info", reason=reason))
        queue_moderation_update(alert, title="A moderator needs more information", message="Your report remains private until the requested information is resolved.")
    elif decision == "reject":
        alert.status = AlertStatus.REJECTED
        alert.published_at = None
        alert.public_summary = None
        db.session.add(ReportAction(alert=alert, actor_id=g.current_user.id, action="moderator_reject", reason=reason))
        queue_moderation_update(alert, title="A moderator closed your report", message="Your report was not published. Open My reports for its current status.")
    else:  # A published abduction can be withdrawn after a post-publication safety review.
        users = db.session.scalars(db.select(User).where(User.is_phone_verified.is_(True))).all()
        former_recipients = eligible_recipients(alert, users)
        alert.status = AlertStatus.WITHDRAWN
        db.session.add(ReportAction(alert=alert, actor_id=g.current_user.id, action="moderator_withdraw", reason=reason))
        queue_closure_notifications(alert, former_recipients, action="withdrawn")
        queue_moderation_update(alert, title="A moderator withdrew your alert", message="Your published report is no longer visible in the community feed.")

    db.session.commit()
    return redirect(url_for("main.moderator_queue"))


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
    selected_filter = request.args.get("filter", "all").strip()
    if selected_filter not in {"all", "unread", "read"}:
        selected_filter = "all"
    unread_count = db.session.scalar(
        db.select(db.func.count(Notification.id)).where(
            Notification.recipient_id == g.current_user.id,
            Notification.is_read.is_(False),
        )
    )
    return render_template(
        "notifications.html",
        active_page=None,
        app_shell=True,
        notifications=notification_views_for_user(g.current_user, filter_name=selected_filter),
        selected_filter=selected_filter,
        unread_count=unread_count,
    )


@bp.post("/notifications/mark-seen")
@login_required
def mark_notifications_seen():
    """Explicitly mark every unread persisted notification as read for this recipient."""
    unread_notifications = db.session.scalars(
        db.select(Notification).where(
            Notification.recipient_id == g.current_user.id,
            Notification.is_read.is_(False),
        )
    ).all()
    for notification in unread_notifications:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
    db.session.commit()
    selected_filter = request.form.get("filter", "all").strip()
    if selected_filter not in {"all", "unread", "read"}:
        selected_filter = "all"
    return redirect(url_for("main.notifications", filter=selected_filter))


@bp.get("/notifications/<notification_id>/open")
@login_required
def open_notification(notification_id: str):
    """Mark one item read, then open its alert, review, or safe status update."""
    notification = owned_notification(notification_id)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.session.commit()
    alert = notification.alert
    if notification.kind == "administrative_request" and g.current_user.role == UserRole.ADMINISTRATOR:
        if notification.administrative_request_type == "hospital_verification" and notification.administrative_request_id:
            if db.session.get(HospitalVerificationRequest, notification.administrative_request_id):
                return redirect(url_for("main.administrator_hospital_verification_detail", request_id=notification.administrative_request_id))
        if notification.administrative_request_type == "moderator_access" and notification.administrative_request_id:
            if db.session.get(ModeratorAccessRequest, notification.administrative_request_id):
                return redirect(url_for("main.administrator_moderator_request_detail", request_id=notification.administrative_request_id))
    if notification.kind == "alert_published" and alert and user_receives_alert(g.current_user, alert):
        return redirect(url_for("main.alert_detail", alert_id=alert.id))
    if notification.kind == "report_published" and alert and alert.reporter_id == g.current_user.id:
        # Published reports use their public-safe alert page regardless of the incident category.
        return redirect(url_for("main.alert_detail", alert_id=alert.id))
    if notification.kind == "report_needs_moderation" and alert and alert.reporter_id == g.current_user.id:
        if alert.alert_type == AlertType.MISSING_PERSON and alert.ai_review:
            return redirect(url_for("main.ai_review", alert_id=alert.id))
        if alert.alert_type == AlertType.SUSPECTED_ABDUCTION and alert.ai_review:
            return redirect(url_for("main.suspected_abduction_ai_review", alert_id=alert.id))
        if alert.alert_type == AlertType.ROAD_ACCIDENT:
            return redirect(url_for("main.road_accident_report_submitted", alert_id=alert.id))
        return redirect(url_for("main.my_reports"))
    if notification.kind in {"reported_found", "withdrawn"} and alert and alert.reporter_id == g.current_user.id:
        return redirect(url_for("main.my_reports"))
    return render_template(
        "notification_detail.html",
        active_page=None,
        app_shell=True,
        notification=notification_view(notification),
    )


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
