"""Tests for the PRD’s publication thresholds and safety blocks."""

from types import SimpleNamespace
import unittest

from app.models import AlertStatus
from app.publication import decide_publication


def review(*, confidence: int = 80, fraud_risk: int = 79, missing_fields=None, duplicates=None):
    return SimpleNamespace(
        confidence_score=confidence,
        fraud_risk_score=fraud_risk,
        missing_fields=[] if missing_fields is None else missing_fields,
        duplicate_candidates=[] if duplicates is None else duplicates,
    )


class PublicationRuleTestCase(unittest.TestCase):
    def test_publishes_at_the_exact_confidence_and_fraud_thresholds(self) -> None:
        decision = decide_publication(review(confidence=80, fraud_risk=79))
        self.assertEqual(decision.status, AlertStatus.PUBLISHED)

    def test_routes_low_confidence_or_high_fraud_to_moderation(self) -> None:
        low_confidence = decide_publication(review(confidence=79, fraud_risk=0))
        high_fraud = decide_publication(review(confidence=100, fraud_risk=80))
        self.assertEqual(low_confidence.status, AlertStatus.NEEDS_MODERATION)
        self.assertEqual(high_fraud.status, AlertStatus.NEEDS_MODERATION)

    def test_routes_missing_information_and_duplicates_to_moderation(self) -> None:
        missing_data = decide_publication(review(missing_fields=["photo"]))
        duplicate = decide_publication(review(duplicates=[{"alert_id": "active-1"}]))
        self.assertEqual(missing_data.status, AlertStatus.NEEDS_MODERATION)
        self.assertEqual(duplicate.status, AlertStatus.NEEDS_MODERATION)


if __name__ == "__main__":
    unittest.main()
