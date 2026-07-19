"""Tests for editable alert category, region, and e-mail preferences."""

import unittest

from app import create_app
from app.extensions import db
from app.models import AlertPreference, User


class PreferenceTestCase(unittest.TestCase):
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
        self.user = User(
            phone_number="+237699000000",
            display_name="Preference tester",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        db.session.add(self.user)
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = self.user.id

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_settings_saves_categories_regions_and_email_choice(self) -> None:
        response = self.client.post(
            "/settings",
            data={
                "enabled_categories": ["missing_person", "road_accident"],
                "followed_regions": ["Littoral", "Ouest"],
            },
        )
        self.assertTrue(response.headers["Location"].endswith("/dashboard"))

        preference = db.session.scalar(
            db.select(AlertPreference).where(AlertPreference.user_id == self.user.id)
        )
        self.assertEqual(preference.enabled_categories, ["missing_person", "road_accident"])
        self.assertEqual(preference.followed_regions, ["Littoral", "Ouest"])
        self.assertFalse(preference.email_notifications_enabled)

    def test_settings_requires_an_alert_category(self) -> None:
        response = self.client.post(
            "/settings",
            data={"followed_regions": "Littoral"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Choose at least one alert category", response.data)
        self.assertIsNone(
            db.session.scalar(
                db.select(AlertPreference).where(AlertPreference.user_id == self.user.id)
            )
        )

    def test_settings_rejects_a_region_outside_the_profile_country(self) -> None:
        response = self.client.post(
            "/settings",
            data={
                "enabled_categories": "missing_person",
                "followed_regions": "Estuaire",
                "email_notifications_enabled": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Choose followed regions from your selected country", response.data)


if __name__ == "__main__":
    unittest.main()
