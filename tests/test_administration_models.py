"""T41 model and validation coverage for future administration workflows."""

import unittest

from app import create_app
from app.administration import ensure_default_safety_rules, record_administration_audit
from app.extensions import db
from app.models import (
    AdministrationAuditEntry,
    HospitalVerificationRequest,
    HospitalVerificationStatus,
    SAFETY_RULE_SPECS,
    SafetyRule,
    SafetyRuleKey,
    User,
    UserRole,
    utc_now,
)


class AdministrationModelTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.applicant = User(
            phone_number="+237692000041", country="Cameroon", primary_region="Centre", is_phone_verified=True
        )
        self.admin = User(
            phone_number="+237692000042", country="Cameroon", primary_region="Centre",
            role=UserRole.ADMINISTRATOR, is_phone_verified=True,
        )
        db.session.add_all([self.applicant, self.admin])
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def valid_hospital_request(self) -> HospitalVerificationRequest:
        return HospitalVerificationRequest(
            submitted_by_id=self.applicant.id,
            hospital_name="Mfoundi Community Hospital",
            country="Cameroon",
            region="Centre",
            contact_name="Dr. Ndom",
            contact_phone="+237690123456",
            supporting_document_reference="hospital_verification/private/mfoundi-registration.pdf",
        )

    def test_hospital_request_requires_private_submission_fields_and_reasoned_final_decision(self) -> None:
        request = self.valid_hospital_request()
        self.assertEqual(request.submission_validation_errors(), {})
        db.session.add(request)
        db.session.flush()
        self.assertEqual(request.status, HospitalVerificationStatus.PENDING)

        request.status = HospitalVerificationStatus.APPROVED
        errors = request.decision_validation_errors()
        self.assertIn("reviewed_by_id", errors)
        self.assertIn("reviewed_at", errors)
        self.assertIn("decision_reason", errors)

        request.reviewed_by_id = self.admin.id
        request.reviewed_at = utc_now()
        request.decision_reason = "Registration evidence and institution contact were reviewed."
        self.assertEqual(request.decision_validation_errors(), {})

        request.contact_phone = "bad"
        self.assertIn("contact_phone", request.submission_validation_errors())

    def test_safety_rules_have_safe_defaults_and_rule_specific_bounds(self) -> None:
        rules = ensure_default_safety_rules()
        db.session.commit()
        self.assertEqual(len(rules), len(SAFETY_RULE_SPECS))
        self.assertEqual(db.session.scalar(db.select(db.func.count(SafetyRule.id))), len(SAFETY_RULE_SPECS))
        self.assertTrue(all(not rule.validation_errors() for rule in rules))

        confidence = db.session.scalar(
            db.select(SafetyRule).where(SafetyRule.key == SafetyRuleKey.MINIMUM_PUBLICATION_CONFIDENCE)
        )
        confidence.value = 49
        self.assertIn("value", confidence.validation_errors())
        confidence.value = 81
        self.assertEqual(confidence.validation_errors(), {})

        fraud = SafetyRule(key=SafetyRuleKey.MAXIMUM_PUBLICATION_FRAUD_RISK, value=81)
        self.assertIn("value", fraud.validation_errors())
        expiry = SafetyRule(key=SafetyRuleKey.ROAD_ACCIDENT_EXPIRY_HOURS, value=73)
        self.assertIn("value", expiry.validation_errors())

    def test_administration_audit_preserves_actor_reason_values_and_is_immutable(self) -> None:
        entry = record_administration_audit(
            actor_id=self.admin.id,
            action="hospital_verification_approved",
            reason="Registration evidence was checked.",
            prior_value={"status": "pending"},
            new_value={"status": "approved", "role": "hospital_representative"},
            target_user_id=self.applicant.id,
        )
        db.session.commit()
        stored = db.session.get(AdministrationAuditEntry, entry.id)
        self.assertEqual(stored.actor_id, self.admin.id)
        self.assertEqual(stored.prior_value, {"status": "pending"})
        self.assertEqual(stored.new_value["role"], "hospital_representative")

        stored.reason = "Changed later"
        with self.assertRaisesRegex(ValueError, "immutable"):
            db.session.commit()
        db.session.rollback()

        stored = db.session.get(AdministrationAuditEntry, entry.id)
        db.session.delete(stored)
        with self.assertRaisesRegex(ValueError, "immutable"):
            db.session.commit()
        db.session.rollback()

    def test_administration_audit_rejects_missing_reason_or_unsafe_action(self) -> None:
        with self.assertRaisesRegex(ValueError, "reason"):
            record_administration_audit(actor_id=self.admin.id, action="role_changed", reason=" ")
        with self.assertRaisesRegex(ValueError, "machine-readable"):
            record_administration_audit(actor_id=self.admin.id, action="role changed!", reason="Explained.")


if __name__ == "__main__":
    unittest.main()
