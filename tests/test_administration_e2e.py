"""T48 end-to-end administrator demonstration workflow."""

import unittest

from app import create_app
from app.extensions import db
from app.models import AIReview, AdministrationAuditEntry, Alert, AlertStatus, AlertType, HospitalVerificationRequest, ReportAction, SafetyRule, SafetyRuleKey, User, UserRole


class AdministrationEndToEndTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = User(phone_number="+237692000111", display_name="Demo Administrator", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        self.applicant = User(phone_number="+237692000112", display_name="Demo Hospital Applicant", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        self.reporter = User(phone_number="+237692000113", display_name="Demo Reporter", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        db.session.add_all([self.admin, self.applicant, self.reporter])
        db.session.flush()
        self.alert = Alert(reporter=self.reporter, alert_type=AlertType.MISSING_PERSON, title="Private E2E moderation report", country="Cameroon", region="Centre", status=AlertStatus.NEEDS_MODERATION)
        db.session.add(self.alert)
        db.session.flush()
        db.session.add(AIReview(
            alert=self.alert,
            public_summary="A safe public summary for the authorised moderator workflow.",
            extracted_data={}, missing_fields=[], duplicate_candidates=[], confidence_score=72,
            fraud_risk_score=10, decision="needs_moderation", reasons=["Human review required."], source="test",
        ))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    @staticmethod
    def safety_rule_form(**overrides: str) -> dict[str, str]:
        values = {
            "rule_minimum_publication_confidence": "80",
            "rule_maximum_publication_fraud_risk": "80",
            "rule_road_accident_expiry_hours": "24",
            "rule_unknown_hospital_patient_expiry_hours": "72",
            "reason": "Approved operational safety adjustment for the demo.",
        }
        values.update(overrides)
        return values

    def test_administrator_demo_journey_covers_authorisation_roles_rules_audit_and_moderation(self) -> None:
        # A verified citizen cannot enter restricted administration before the workflow starts.
        self.sign_in_as(self.applicant)
        self.assertEqual(self.client.get("/admin").status_code, 403)

        # The citizen submits a private hospital-verification request.
        request_response = self.client.post("/hospital-verification/request", data={
            "hospital_name": "Demo Centre Hospital",
            "contact_name": "Demo Hospital Applicant",
            "contact_phone": "+237692000112",
            "supporting_document_reference": "private/demo-hospital-registration.pdf",
        })
        self.assertEqual(request_response.status_code, 302)
        verification = db.session.scalar(db.select(HospitalVerificationRequest))
        self.assertIsNotNone(verification)

        # The administrator can review, approve, then grant the same account moderation access.
        self.sign_in_as(self.admin)
        self.assertEqual(self.client.get("/admin/hospital-verifications").status_code, 200)
        approval = self.client.post(
            f"/admin/hospital-verifications/{verification.id}/decision",
            data={"decision": "approve", "reason": "The private registration evidence was checked for this demo."},
        )
        self.assertEqual(approval.status_code, 302)
        self.assertEqual(db.session.get(User, self.applicant.id).role, UserRole.HOSPITAL_REPRESENTATIVE)
        grant = self.client.post(
            f"/admin/moderators/{self.applicant.id}/role",
            data={"action": "grant", "reason": "Temporary supervised moderation coverage for the demo."},
        )
        self.assertEqual(grant.status_code, 302)
        self.assertEqual(db.session.get(User, self.applicant.id).role, UserRole.MODERATOR)

        # Safety-rule bounds are enforced before a valid future-facing update is accepted.
        rejected_rule = self.client.post("/admin/safety-rules", data=self.safety_rule_form(rule_road_accident_expiry_hours="73"))
        self.assertEqual(rejected_rule.status_code, 200)
        self.assertIn(b"must be between 1 and 72", rejected_rule.data)
        saved_rule = self.client.post("/admin/safety-rules", data=self.safety_rule_form(rule_minimum_publication_confidence="85"))
        self.assertEqual(saved_rule.status_code, 302)
        rule = db.session.scalar(db.select(SafetyRule).where(SafetyRule.key == SafetyRuleKey.MINIMUM_PUBLICATION_CONFIDENCE))
        self.assertEqual(rule.value, 85)

        # The newly granted moderator completes a human decision; it becomes visible to admins as an audit event.
        self.sign_in_as(self.applicant)
        self.assertEqual(self.client.get("/moderator").status_code, 200)
        decision = self.client.post(
            f"/moderator/alerts/{self.alert.id}/decision",
            data={"decision": "publish", "reason": "The public summary is safe and a human review approved publication."},
        )
        self.assertEqual(decision.status_code, 302)
        self.assertEqual(db.session.get(Alert, self.alert.id).status, AlertStatus.PUBLISHED)
        self.assertIsNotNone(db.session.scalar(db.select(ReportAction).where(ReportAction.action == "moderator_publish")))

        self.sign_in_as(self.admin)
        audit_log = self.client.get("/admin/audit-log?action=moderator_publish")
        self.assertEqual(audit_log.status_code, 200)
        self.assertIn(b"Moderator Publish", audit_log.data)
        dashboard = self.client.get("/admin")
        self.assertIn(b"Active alerts", dashboard.data)
        self.assertIn(b"Demo Hospital Applicant", dashboard.data)
        actions = db.session.scalars(db.select(AdministrationAuditEntry.action)).all()
        self.assertTrue({"hospital_verification_approved", "moderator_granted", "safety_rule_updated"}.issubset(set(actions)))


if __name__ == "__main__":
    unittest.main()
