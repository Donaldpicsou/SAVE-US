"""Coverage for the private polling snapshot used by the application shell."""

import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertPreference, AlertStatus, AlertType, Notification, User


class LiveStatusTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(phone_number="+237655100001", display_name="Amina", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        reporter = User(phone_number="+237655100002", display_name="Reporter", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        db.session.add_all((self.user, reporter, AlertPreference(user=self.user, enabled_categories=["missing_person"], followed_regions=[])))
        db.session.flush()
        self.alert = Alert(reporter=reporter, alert_type=AlertType.MISSING_PERSON, status=AlertStatus.PUBLISHED, title="Nadia Mbarga", public_summary="Public search notice.", country="Cameroon", region="Centre", approximate_zone="Public area")
        db.session.add(self.alert)
        db.session.flush()
        db.session.add(Notification(recipient=self.user, alert=self.alert, kind="alert_published", title="New alert", body="A new alert is available.", public_location="Centre"))
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = self.user.id

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_status_is_private_no_cache_and_contains_only_live_shell_data(self) -> None:
        response = self.client.get("/live-status")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store, max-age=0")
        payload = response.get_json()
        self.assertEqual(payload["notification_count"], 1)
        self.assertEqual(payload["alert_count"], 1)
        self.assertEqual(payload["latest_alert_id"], self.alert.id)
        self.assertEqual(payload["notification_items"][0]["title"], "New alert")
        self.assertNotIn("private_contact", payload)

    def test_status_requires_a_signed_in_user(self) -> None:
        anonymous = self.app.test_client().get("/live-status")
        self.assertEqual(anonymous.status_code, 302)


if __name__ == "__main__":
    unittest.main()
