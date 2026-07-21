"""Private administrator work-inbox coverage: counters, notifications, and role requests."""

import unittest

from app import create_app
from app.extensions import db
from app.models import (
    AdministrationAuditEntry,
    HospitalVerificationRequest,
    ModeratorAccessRequest,
    ModeratorAccessRequestStatus,
    Notification,
    User,
    UserRole,
)


class AdministratorWorkInboxTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = User(phone_number="+237692000151", display_name="Inbox Admin", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        self.applicant = User(phone_number="+237692000152", display_name="Community Reviewer", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        db.session.add_all([self.admin, self.applicant])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def test_hospital_submission_notifies_administrator_and_updates_workspace_counter(self) -> None:
        self.sign_in_as(self.applicant)
        response = self.client.post(
            "/hospital-verification/request",
            data={
                "hospital_name": "Inbox Hospital",
                "contact_name": "Community Reviewer",
                "contact_phone": "+237692000152",
                "supporting_document_reference": "private/inbox-evidence.pdf",
            },
        )
        self.assertEqual(response.status_code, 302)
        verification_request = db.session.scalar(db.select(HospitalVerificationRequest))
        notification = db.session.scalar(db.select(Notification).where(Notification.recipient_id == self.admin.id))
        self.assertEqual(notification.administrative_request_type, "hospital_verification")
        self.assertEqual(notification.administrative_request_id, verification_request.id)

        self.sign_in_as(self.admin)
        dashboard = self.client.get("/admin")
        self.assertIn(b"Requires your attention", dashboard.data)
        self.assertIn(b"Hospital verifications (1)", dashboard.data)
        self.assertIn(b"Administration", dashboard.data)
        opened = self.client.get(f"/notifications/{notification.id}/open")
        self.assertEqual(opened.status_code, 302)
        self.assertIn(f"/admin/hospital-verifications/{verification_request.id}", opened.headers["Location"])

    def test_moderator_access_request_is_private_notified_and_audited_when_approved(self) -> None:
        self.sign_in_as(self.applicant)
        response = self.client.post(
            "/moderator-access/request",
            data={"reason": "I coordinate a community safety network and can review reports responsibly."},
        )
        self.assertEqual(response.status_code, 302)
        access_request = db.session.scalar(db.select(ModeratorAccessRequest))
        notification = db.session.scalar(db.select(Notification).where(Notification.recipient_id == self.admin.id))
        self.assertEqual(notification.administrative_request_type, "moderator_access")
        self.assertEqual(notification.administrative_request_id, access_request.id)

        self.sign_in_as(self.admin)
        queue = self.client.get("/admin/moderator-requests")
        self.assertEqual(queue.status_code, 200)
        self.assertIn(b"Community Reviewer", queue.data)
        detail = self.client.get(f"/admin/moderator-requests/{access_request.id}")
        self.assertIn(b"community safety network", detail.data)
        decision = self.client.post(
            f"/admin/moderator-requests/{access_request.id}/decision",
            data={"decision": "approve", "reason": "The applicant has suitable verified community-safety experience."},
        )
        self.assertEqual(decision.status_code, 302)
        stored_request = db.session.get(ModeratorAccessRequest, access_request.id)
        self.assertEqual(stored_request.status, ModeratorAccessRequestStatus.APPROVED)
        self.assertEqual(db.session.get(User, self.applicant.id).role, UserRole.MODERATOR)
        audit = db.session.scalar(
            db.select(AdministrationAuditEntry).where(AdministrationAuditEntry.moderator_access_request_id == access_request.id)
        )
        self.assertEqual(audit.action, "moderator_access_request_approved")
        self.assertEqual(audit.new_value, {"status": "approved", "role": "moderator"})
        applicant_notification = db.session.scalar(
            db.select(Notification).where(
                Notification.recipient_id == self.applicant.id,
                Notification.kind == "moderator_access_request_decision",
            )
        )
        self.assertIsNotNone(applicant_notification)

    def test_staff_counters_exclude_resolved_administration_requests(self) -> None:
        request = ModeratorAccessRequest(
            submitted_by=self.applicant,
            reason="I can help with careful, safe community report reviews.",
            status=ModeratorAccessRequestStatus.REJECTED,
        )
        db.session.add(request)
        db.session.commit()
        self.sign_in_as(self.admin)
        page = self.client.get("/admin")
        self.assertIn(b"0 administrative requests awaiting review", page.data)
        self.assertNotIn(b"Administration</span><b class=\"sidebar-badge\"", page.data)


if __name__ == "__main__":
    unittest.main()
