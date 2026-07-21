"""T43 private institution request and administrator decision workflow coverage."""

import unittest

from app import create_app
from app.extensions import db
from app.models import (
    AdministrationAuditEntry,
    HospitalVerificationRequest,
    HospitalVerificationStatus,
    User,
    UserRole,
)


class HospitalVerificationWorkflowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.applicant = User(phone_number="+237692000061", display_name="Dr. Ndom", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        self.admin = User(phone_number="+237692000062", display_name="Admin", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        self.moderator = User(phone_number="+237692000063", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.MODERATOR)
        db.session.add_all([self.applicant, self.admin, self.moderator])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def submit_request(self, user: User | None = None) -> HospitalVerificationRequest:
        self.sign_in_as(user or self.applicant)
        response = self.client.post(
            "/hospital-verification/request",
            data={
                "hospital_name": "Mfoundi Community Hospital",
                "contact_name": "Dr. Ndom",
                "contact_phone": "+237 692 000 061",
                "supporting_document_reference": "private/registration/Mfoundi-2026.pdf",
            },
        )
        self.assertEqual(response.status_code, 302)
        verification_request = db.session.scalar(
            db.select(HospitalVerificationRequest).where(HospitalVerificationRequest.submitted_by_id == self.applicant.id)
        )
        self.assertIsNotNone(verification_request)
        return verification_request

    def test_verified_user_submits_one_private_request_and_cannot_duplicate_it(self) -> None:
        verification_request = self.submit_request()
        self.assertEqual(verification_request.status, HospitalVerificationStatus.PENDING)
        self.assertEqual((verification_request.country, verification_request.region), ("Cameroon", "Centre"))

        response = self.client.post(
            "/hospital-verification/request",
            data={"hospital_name": "Another hospital", "contact_name": "Dr. Ndom", "contact_phone": "+237692000061", "supporting_document_reference": "private/second.pdf"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already awaiting review", response.data)
        self.assertEqual(db.session.scalar(db.select(db.func.count(HospitalVerificationRequest.id))), 1)

    def test_request_rejects_an_invalid_institution_contact_phone(self) -> None:
        self.sign_in_as(self.applicant)
        response = self.client.post(
            "/hospital-verification/request",
            data={"hospital_name": "Mfoundi Community Hospital", "contact_name": "Dr. Ndom", "contact_phone": "123", "supporting_document_reference": "private/registration.pdf"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"valid CEMAC institution contact phone", response.data)
        self.assertEqual(db.session.scalar(db.select(db.func.count(HospitalVerificationRequest.id))), 0)

    def test_only_administrator_can_view_private_evidence_and_approval_grants_role_with_audit(self) -> None:
        verification_request = self.submit_request()
        self.sign_in_as(self.moderator)
        self.assertEqual(self.client.get("/admin/hospital-verifications").status_code, 403)
        self.assertEqual(self.client.get(f"/admin/hospital-verifications/{verification_request.id}").status_code, 403)

        self.sign_in_as(self.admin)
        queue = self.client.get("/admin/hospital-verifications")
        self.assertEqual(queue.status_code, 200)
        self.assertIn(b"Mfoundi Community Hospital", queue.data)
        detail = self.client.get(f"/admin/hospital-verifications/{verification_request.id}")
        self.assertIn(b"private/registration/Mfoundi-2026.pdf", detail.data)
        self.assertIn(b"+237692000061", detail.data)

        response = self.client.post(
            f"/admin/hospital-verifications/{verification_request.id}/decision",
            data={"decision": "approve", "reason": "Registration evidence and institution contact were verified."},
        )
        self.assertEqual(response.status_code, 302)
        stored_request = db.session.get(HospitalVerificationRequest, verification_request.id)
        self.assertEqual(stored_request.status, HospitalVerificationStatus.APPROVED)
        self.assertEqual((stored_request.reviewed_by_id, db.session.get(User, self.applicant.id).role), (self.admin.id, UserRole.HOSPITAL_REPRESENTATIVE))
        audit = db.session.scalar(
            db.select(AdministrationAuditEntry).where(
                AdministrationAuditEntry.hospital_verification_request_id == verification_request.id
            )
        )
        self.assertEqual(audit.action, "hospital_verification_approved")
        self.assertEqual(audit.prior_value, {"status": "pending", "role": "citizen"})
        self.assertEqual(audit.new_value, {"status": "approved", "role": "hospital_representative"})
        self.assertEqual(self.client.post(f"/admin/hospital-verifications/{verification_request.id}/decision", data={"decision": "reject", "reason": "late"}).status_code, 409)

    def test_rejection_requires_reason_and_never_grants_hospital_role(self) -> None:
        verification_request = self.submit_request()
        self.sign_in_as(self.admin)
        missing_reason = self.client.post(
            f"/admin/hospital-verifications/{verification_request.id}/decision",
            data={"decision": "reject", "reason": ""},
        )
        self.assertEqual(missing_reason.status_code, 302)
        self.assertIn("error=", missing_reason.headers["Location"])
        self.assertEqual(db.session.get(HospitalVerificationRequest, verification_request.id).status, HospitalVerificationStatus.PENDING)

        self.client.post(
            f"/admin/hospital-verifications/{verification_request.id}/decision",
            data={"decision": "reject", "reason": "The supporting evidence could not be confirmed."},
        )
        self.assertEqual(db.session.get(HospitalVerificationRequest, verification_request.id).status, HospitalVerificationStatus.REJECTED)
        self.assertEqual(db.session.get(User, self.applicant.id).role, UserRole.CITIZEN)


if __name__ == "__main__":
    unittest.main()
