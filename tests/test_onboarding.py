"""Tests for CEMAC location onboarding and profile persistence."""

import unittest

from app import create_app
from app.extensions import db
from app.models import AlertPreference, User


class OnboardingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
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

    def test_verified_new_phone_requires_display_name_before_creating_location_profile(self) -> None:
        self.client.post("/sign-in", data={"phone_number": "+237600000000"})
        response = self.client.post("/verify-otp", data={"otp_code": "123456"})
        self.assertTrue(response.headers["Location"].endswith("/onboarding/profile"))

        missing_name = self.client.post("/onboarding/profile", data={"display_name": " "})
        self.assertEqual(missing_name.status_code, 200)
        self.assertIn(b"display name between 2 and 120", missing_name.data)
        self.assertIsNone(db.session.scalar(db.select(User).where(User.phone_number == "+237600000000")))

        response = self.client.post("/onboarding/profile", data={"display_name": "  Amina   Community  "})
        self.assertTrue(response.headers["Location"].endswith("/onboarding/location"))

        response = self.client.post(
            "/onboarding/location",
            data={"country_code": "gabon", "primary_region": "Estuaire"},
        )
        self.assertTrue(response.headers["Location"].endswith("/onboarding/preferences"))

        user = db.session.scalar(db.select(User).where(User.phone_number == "+237600000000"))
        self.assertEqual((user.display_name, user.country, user.primary_region), ("Amina Community", "Gabon", "Estuaire"))
        self.assertTrue(user.is_phone_verified)

        response = self.client.post(
            "/onboarding/preferences",
            data={
                "enabled_categories": "missing_person",
                "followed_regions": "Haut-Ogooué",
                "email_notifications_enabled": "on",
            },
        )
        self.assertTrue(response.headers["Location"].endswith("/dashboard"))
        self.assertEqual(
            db.session.scalar(
                db.select(AlertPreference).where(AlertPreference.user_id == user.id)
            ).followed_regions,
            ["Haut-Ogooué"],
        )

    def test_invalid_region_is_not_saved(self) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["onboarding_phone"] = "+237600000001"
            browser_session["onboarding_display_name"] = "Valid Profile"
        response = self.client.post(
            "/onboarding/location",
            data={"country_code": "gabon", "primary_region": "Centre"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Choose a valid province", response.data)
        self.assertIsNone(
            db.session.scalar(db.select(User).where(User.phone_number == "+237600000001"))
        )

    def test_location_step_redirects_to_profile_when_name_has_not_been_collected(self) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["onboarding_phone"] = "+237600000002"
        response = self.client.get("/onboarding/location")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/onboarding/profile"))


if __name__ == "__main__":
    unittest.main()
