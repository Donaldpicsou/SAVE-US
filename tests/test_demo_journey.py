"""End-to-end Cameroon/Centre demonstration journey required by roadmap T20."""

import io
import tempfile
import unittest

from app import create_app
from app.extensions import db
from app.models import AIReview, Alert, AlertPreference, AlertStatus, User


class CameroonCentreDemoJourneyTestCase(unittest.TestCase):
    """A new community member completes the main hackathon demonstration flow."""

    def setUp(self) -> None:
        self.upload_directory = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "UPLOAD_FOLDER": self.upload_directory.name,
            }
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.upload_directory.cleanup()

    @staticmethod
    def valid_png() -> bytes:
        return b"\x89PNG\r\n\x1a\n" + b"save-us-demo-journey-image"

    def test_new_cameroon_centre_user_can_publish_and_receive_a_missing_person_alert(self) -> None:
        # 1. OTP signup, required profile name, and location onboarding.
        response = self.client.post("/sign-in", data={"phone_number": "+237 699 000 000"})
        self.assertIn("/verify-otp", response.headers["Location"])
        response = self.client.post("/verify-otp", data={"otp_code": "123456"})
        self.assertIn("/onboarding/profile", response.headers["Location"])
        response = self.client.post("/onboarding/profile", data={"display_name": "Centre Community"})
        self.assertIn("/onboarding/location", response.headers["Location"])
        response = self.client.post(
            "/onboarding/location",
            data={"country_code": "cameroun", "primary_region": "Centre"},
        )
        self.assertIn("/onboarding/preferences", response.headers["Location"])

        # 2. The subscriber enables the categories used by the primary demo.
        response = self.client.post(
            "/onboarding/preferences",
            data={
                "enabled_categories": ["missing_person", "suspected_abduction"],
                "email_notifications_enabled": "on",
            },
        )
        self.assertTrue(response.headers["Location"].endswith("/dashboard"))
        subscriber = db.session.scalar(db.select(User).where(User.phone_number == "+237699000000"))
        self.assertEqual((subscriber.display_name, subscriber.country, subscriber.primary_region), ("Centre Community", "Cameroon", "Centre"))
        self.assertEqual(subscriber.alert_preference.enabled_categories, ["missing_person", "suspected_abduction"])
        self.assertTrue(subscriber.alert_preference.email_notifications_enabled)

        # 3. The reporter submits a complete Cameroon/Centre missing-person report.
        response = self.client.post(
            "/report/missing-person",
            data={
                "action": "review",
                "name": "Amadou Njoya",
                "age": "12",
                "sex": "male",
                "photo": (io.BytesIO(self.valid_png()), "amadou.png", "image/png"),
                "last_seen_at": "2026-07-19T10:30",
                "approximate_zone": "Mfoundi district, Yaoundé",
                "last_seen_location": "Near the central market",
                "clothing_description": "Blue shirt and black backpack",
                "private_family_contact": "+237 699 000 000",
                "circumstances": "He did not return after leaving the central market.",
            },
            content_type="multipart/form-data",
        )
        self.assertIn("/reviewing", response.headers["Location"])

        # 4. Deterministic AI fallback reviews the report, T17 publishes it, and the review is visible.
        review = db.session.scalar(db.select(AIReview))
        alert = db.session.get(Alert, review.alert_id)
        self.assertEqual((alert.country, alert.region), ("Cameroon", "Centre"))
        self.assertEqual(alert.status, AlertStatus.PUBLISHED)
        self.assertGreaterEqual(review.confidence_score, 80)
        self.assertLess(review.fraud_risk_score, 80)
        review_screen = self.client.get(f"/reports/{alert.id}/ai-review")
        self.assertEqual(review_screen.status_code, 200)
        self.assertIn(b"Alert published", review_screen.data)

        # 5. The same subscriber receives the targeted alert in the filtered feed and can open it.
        feed = self.client.get("/alerts?type=missing_person&q=amadou")
        self.assertEqual(feed.status_code, 200)
        self.assertIn(b"Amadou Njoya", feed.data)
        self.assertIn(f"/alerts/{alert.id}".encode(), feed.data)
        self.assertIn(f"/alerts/{alert.id}/photo".encode(), feed.data)
        detail = self.client.get(f"/alerts/{alert.id}")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Mfoundi district, Yaound", detail.data)
        self.assertIn(f"/alerts/{alert.id}/photo".encode(), detail.data)
        self.assertNotIn(b"+237 699 000 000", detail.data)
        photo = self.client.get(f"/alerts/{alert.id}/photo")
        self.assertEqual(photo.status_code, 200)
        self.assertEqual(photo.data, self.valid_png())
        self.assertIn("private, no-store", photo.headers["Cache-Control"])
        photo.close()

        # A subscriber outside the alert country cannot fetch the same private source file.
        outsider = User(
            phone_number="+24174001122",
            country="Gabon",
            primary_region="Estuaire",
            is_phone_verified=True,
        )
        db.session.add_all([
            outsider,
            AlertPreference(user=outsider, enabled_categories=["missing_person"]),
        ])
        db.session.commit()
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = outsider.id
        self.assertEqual(self.client.get(f"/alerts/{alert.id}/photo").status_code, 404)


if __name__ == "__main__":
    unittest.main()
