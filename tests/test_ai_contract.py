"""Tests for the versioned structured AI-review contract."""

from datetime import timedelta
import unittest

from app import create_app
from app.ai_contract import (
    AI_REVIEW_SCHEMA_VERSION,
    AIContractValidationError,
    build_missing_person_review_input,
    validate_ai_review_output,
)
from app.ai_fallback import FALLBACK_REVIEW_SOURCE, deterministic_ai_review
from app.ai_service import OPENAI_REVIEW_SOURCE, review_with_openai_or_fallback
from app.extensions import db
from app.models import Alert, AlertType, MissingPersonDetails, User, utc_now


class AIContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        user = User(phone_number="+237633333333", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        self.alert = Alert(
            reporter=user,
            alert_type=AlertType.MISSING_PERSON,
            title="Jean Bakary, 8",
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi district",
        )
        self.details = MissingPersonDetails(
            alert=self.alert,
            name="Jean Bakary",
            age=8,
            sex="male",
            photo_path="missing_person/demo/jean.png",
            last_seen_at=utc_now() - timedelta(hours=2),
            last_seen_location="Near the primary school",
            clothing_description="Blue school uniform",
            private_family_contact="+237 612 345 678",
            circumstances="Did not return home after school.",
        )
        db.session.add_all([user, self.alert, self.details])
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def valid_output(self) -> dict:
        return {
            "schema_version": AI_REVIEW_SCHEMA_VERSION,
            "public_summary": "Jean Bakary, age 8, was last seen in the Mfoundi district of Yaoundé.",
            "extracted_data": {"name": "Jean Bakary", "age": 8, "sex": "male"},
            "missing_fields": [],
            "duplicate_candidates": [
                {"alert_id": "existing-alert-1", "similarity_score": 46, "matching_factors": ["same district"]}
            ],
            "confidence_score": 86,
            "fraud_risk_score": 14,
            "decision": "publish_candidate",
            "reasons": ["All required fields are present.", "No high-confidence duplicate was found."],
        }

    def test_input_contract_excludes_private_family_contact(self) -> None:
        payload = build_missing_person_review_input(self.alert)
        self.assertEqual(payload["schema_version"], AI_REVIEW_SCHEMA_VERSION)
        self.assertTrue(payload["report"]["photo_available"])
        self.assertNotIn("private_family_contact", payload["report"]["details"])
        self.assertEqual(payload["duplicate_search_scope"]["active_statuses"], ["ai_review", "needs_moderation", "published"])

    def test_valid_output_is_normalised(self) -> None:
        output = validate_ai_review_output(self.valid_output())
        self.assertEqual(output["confidence_score"], 86)
        self.assertEqual(output["duplicate_candidates"][0]["similarity_score"], 46)

    def test_invalid_scores_and_output_keys_are_rejected(self) -> None:
        output = self.valid_output()
        output["confidence_score"] = 101
        with self.assertRaisesRegex(AIContractValidationError, "confidence_score"):
            validate_ai_review_output(output)

        output = self.valid_output()
        output["unsafe_extra"] = True
        with self.assertRaisesRegex(AIContractValidationError, "unexpected keys"):
            validate_ai_review_output(output)

    def test_deterministic_fallback_returns_a_publish_candidate_for_complete_data(self) -> None:
        review_input = build_missing_person_review_input(self.alert)
        first_result = deterministic_ai_review(review_input)
        second_result = deterministic_ai_review(review_input)
        self.assertEqual(FALLBACK_REVIEW_SOURCE, "deterministic_demo_fallback")
        self.assertEqual(first_result, second_result)
        self.assertEqual(first_result["decision"], "publish_candidate")
        self.assertEqual((first_result["confidence_score"], first_result["fraud_risk_score"]), (88, 12))

    def test_deterministic_fallback_handles_missing_fields_and_demo_duplicates(self) -> None:
        review_input = build_missing_person_review_input(self.alert)
        review_input["report"]["photo_available"] = False
        missing_result = deterministic_ai_review(review_input)
        self.assertEqual(missing_result["decision"], "needs_information")
        self.assertIn("photo", missing_result["missing_fields"])

        review_input = build_missing_person_review_input(self.alert)
        review_input["report"]["details"]["name"] = "Samuel Mbo"
        duplicate_result = deterministic_ai_review(review_input)
        self.assertEqual(duplicate_result["decision"], "needs_moderation")
        self.assertEqual(duplicate_result["duplicate_candidates"][0]["similarity_score"], 91)

    def test_live_response_is_validated_and_marks_openai_as_its_source(self) -> None:
        class FakeResponses:
            def __init__(self, output_text: str) -> None:
                self.output_text = output_text
                self.request = None

            def create(self, **kwargs):
                self.request = kwargs
                return type("FakeResponse", (), {"output_text": self.output_text})()

        fake_responses = FakeResponses(__import__("json").dumps(self.valid_output()))
        fake_client = type("FakeClient", (), {"responses": fake_responses})()
        execution = review_with_openai_or_fallback(
            build_missing_person_review_input(self.alert),
            api_key="test-key",
            client_factory=lambda **_: fake_client,
        )
        self.assertEqual(execution.source, OPENAI_REVIEW_SOURCE)
        self.assertIsNone(execution.fallback_reason)
        self.assertTrue(fake_responses.request["text"]["format"]["strict"])
        self.assertFalse(fake_responses.request["store"])

    def test_missing_key_or_invalid_live_response_uses_deterministic_fallback(self) -> None:
        review_input = build_missing_person_review_input(self.alert)
        execution = review_with_openai_or_fallback(review_input, api_key=None)
        self.assertEqual(execution.source, FALLBACK_REVIEW_SOURCE)
        self.assertIn("not configured", execution.fallback_reason)

        invalid_client = type(
            "InvalidClient",
            (),
            {"responses": type("InvalidResponses", (), {"create": lambda self, **_: type("Response", (), {"output_text": "{}"})()})()},
        )()
        execution = review_with_openai_or_fallback(
            review_input,
            api_key="test-key",
            client_factory=lambda **_: invalid_client,
        )
        self.assertEqual(execution.source, FALLBACK_REVIEW_SOURCE)
        self.assertIn("Live AI review unavailable", execution.fallback_reason)


if __name__ == "__main__":
    unittest.main()
