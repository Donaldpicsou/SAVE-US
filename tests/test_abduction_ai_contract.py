"""Tests for the versioned suspected-abduction AI review contract."""

from datetime import timedelta
import unittest

from app import create_app
from app.abduction_ai_contract import (
    ABDUCTION_AI_REVIEW_SCHEMA_VERSION,
    AIContractValidationError,
    build_suspected_abduction_review_input,
    validate_suspected_abduction_review_output,
)
from app.extensions import db
from app.models import Alert, AlertType, SuspectedAbductionDetails, User, utc_now


class AbductionAIContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = User(phone_number="+237699000020", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        self.alert = Alert(
            reporter=user,
            alert_type=AlertType.SUSPECTED_ABDUCTION,
            title="Possible abduction near Mfoundi",
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi district",
        )
        self.details = SuspectedAbductionDetails(
            alert=self.alert,
            photo_path="suspected_abduction/demo/evidence.png",
            abduction_at=utc_now() - timedelta(hours=2),
            description="Witnesses reported that a child was taken near the market.",
            circumstances="A vehicle left the area immediately afterwards.",
            private_contact="+237 699 000 020",
        )
        db.session.add_all([user, self.alert, self.details])
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def valid_output(self) -> dict:
        return {
            "schema_version": ABDUCTION_AI_REVIEW_SCHEMA_VERSION,
            "public_summary": "A suspected abduction was reported near the Mfoundi district in Cameroon.",
            "extracted_data": {"incident_type": "suspected_abduction", "country": "Cameroon"},
            "missing_fields": [],
            "duplicate_candidates": [
                {"alert_id": "existing-abduction-1", "similarity_score": 42, "matching_factors": ["same district"]}
            ],
            "confidence_score": 83,
            "fraud_risk_score": 17,
            "decision": "publish_candidate",
            "reasons": ["The location and incident time are present.", "No strong duplicate was found."],
        }

    def test_input_contract_excludes_private_contact(self) -> None:
        payload = build_suspected_abduction_review_input(self.alert)
        self.assertEqual(payload["schema_version"], ABDUCTION_AI_REVIEW_SCHEMA_VERSION)
        self.assertTrue(payload["report"]["photo_available"])
        self.assertTrue(payload["report"]["private_contact_available"])
        self.assertNotIn("private_contact", payload["report"]["details"])
        self.assertEqual(payload["duplicate_search_scope"]["alert_type"], "suspected_abduction")

    def test_valid_output_contains_the_required_structured_review_fields(self) -> None:
        output = validate_suspected_abduction_review_output(self.valid_output())
        self.assertEqual(output["confidence_score"], 83)
        self.assertEqual(output["fraud_risk_score"], 17)
        self.assertEqual(output["duplicate_candidates"][0]["similarity_score"], 42)

    def test_contract_rejects_private_phone_in_public_summary_and_unknown_missing_fields(self) -> None:
        output = self.valid_output()
        output["public_summary"] = "Call +237 699 000 020 with information."
        with self.assertRaisesRegex(AIContractValidationError, "private contact"):
            validate_suspected_abduction_review_output(output)

        output = self.valid_output()
        output["missing_fields"] = ["invented_field"]
        with self.assertRaisesRegex(AIContractValidationError, "unsupported field"):
            validate_suspected_abduction_review_output(output)

    def test_contract_rejects_the_wrong_alert_type(self) -> None:
        self.alert.alert_type = AlertType.MISSING_PERSON
        with self.assertRaisesRegex(ValueError, "suspected-abduction"):
            build_suspected_abduction_review_input(self.alert)


if __name__ == "__main__":
    unittest.main()
