"""T45 bounded, audited, future-facing safety-rule management coverage."""

from types import SimpleNamespace
import unittest

from app import create_app
from app.administration import configured_safety_rule_values
from app.extensions import db
from app.models import AdministrationAuditEntry, Alert, AlertStatus, AlertType, SafetyRule, SafetyRuleKey, User, UserRole
from app.publication import apply_publication_decision


class SafetyRuleManagementTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = User(phone_number="+237692000081", display_name="Safety Admin", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        self.citizen = User(phone_number="+237692000082", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        db.session.add_all([self.admin, self.citizen])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def form_values(self, **overrides: str) -> dict[str, str]:
        values = {
            "rule_minimum_publication_confidence": "80",
            "rule_maximum_publication_fraud_risk": "80",
            "rule_road_accident_expiry_hours": "24",
            "rule_unknown_hospital_patient_expiry_hours": "72",
            "reason": "Safety review and approved operational adjustment.",
        }
        values.update(overrides)
        return values

    def test_only_administrators_can_open_the_rule_workspace(self) -> None:
        self.sign_in_as(self.citizen)
        self.assertEqual(self.client.get("/admin/safety-rules").status_code, 403)
        self.sign_in_as(self.admin)
        page = self.client.get("/admin/safety-rules")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Minimum Publication Confidence", page.data)
        self.assertEqual(db.session.scalar(db.select(db.func.count(SafetyRule.id))), 4)

    def test_bounded_change_is_audited_and_controls_a_future_publication_only(self) -> None:
        self.sign_in_as(self.admin)
        response = self.client.post(
            "/admin/safety-rules",
            data=self.form_values(rule_minimum_publication_confidence="90"),
        )
        self.assertEqual(response.status_code, 302)
        confidence = db.session.scalar(db.select(SafetyRule).where(SafetyRule.key == SafetyRuleKey.MINIMUM_PUBLICATION_CONFIDENCE))
        self.assertEqual(confidence.value, 90)
        audit = db.session.scalar(db.select(AdministrationAuditEntry).where(AdministrationAuditEntry.action == "safety_rule_updated"))
        self.assertEqual(audit.prior_value, {"key": "minimum_publication_confidence", "value": 80})
        self.assertEqual(audit.new_value, {"key": "minimum_publication_confidence", "value": 90})

        review = SimpleNamespace(confidence_score=85, fraud_risk_score=10, missing_fields=[], duplicate_candidates=[], public_summary="Safe summary")
        earlier_alert = Alert(reporter=self.citizen, alert_type=AlertType.MISSING_PERSON, title="Earlier decision", country="Cameroon", region="Centre")
        db.session.add(earlier_alert)
        apply_publication_decision(earlier_alert, review)  # Simulates the previously persisted default decision.
        self.assertEqual(earlier_alert.status, AlertStatus.PUBLISHED)
        later_alert = Alert(reporter=self.citizen, alert_type=AlertType.MISSING_PERSON, title="Later decision", country="Cameroon", region="Centre")
        db.session.add(later_alert)
        apply_publication_decision(later_alert, review, safety_rules=configured_safety_rule_values())
        self.assertEqual(later_alert.status, AlertStatus.NEEDS_MODERATION)

    def test_out_of_bounds_or_unexplained_changes_are_rejected_without_audit(self) -> None:
        self.sign_in_as(self.admin)
        invalid = self.client.post("/admin/safety-rules", data=self.form_values(rule_road_accident_expiry_hours="73"))
        self.assertEqual(invalid.status_code, 200)
        self.assertIn(b"must be between 1 and 72", invalid.data)
        no_reason = self.client.post("/admin/safety-rules", data=self.form_values(reason="", rule_maximum_publication_fraud_risk="70"))
        self.assertEqual(no_reason.status_code, 200)
        self.assertIn(b"reason is required", no_reason.data)
        self.assertEqual(db.session.scalar(db.select(db.func.count(AdministrationAuditEntry.id))), 0)


if __name__ == "__main__":
    unittest.main()
