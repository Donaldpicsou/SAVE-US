"""Integration tests for the preference-targeted published-alert feed."""

import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertPreference, AlertStatus, AlertType, User


class AlertFeedTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"}
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(
            phone_number="+237655000000",
            display_name="Amina",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        self.reporter = User(
            phone_number="+237655000001",
            display_name="Reporter",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        db.session.add_all([
            self.user,
            self.reporter,
            AlertPreference(
                user=self.user,
                enabled_categories=["missing_person", "suspected_abduction"],
                followed_regions=["Littoral"],
            ),
        ])
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = self.user.id

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def add_alert(self, title, alert_type, *, region="Centre", status=AlertStatus.PUBLISHED, country="Cameroon"):
        alert = Alert(
            reporter=self.reporter,
            alert_type=alert_type,
            status=status,
            title=title,
            public_summary=f"Public information for {title}.",
            country=country,
            region=region,
            approximate_zone=f"{region} public area",
        )
        db.session.add(alert)
        db.session.commit()
        return alert

    def test_feed_shows_only_targeted_published_alerts(self) -> None:
        centre_missing = self.add_alert("Nadia Mbarga", AlertType.MISSING_PERSON)
        followed_region_missing = self.add_alert("Jean Nfor", AlertType.MISSING_PERSON, region="Littoral")
        countrywide_abduction = self.add_alert("Urgent abduction notice", AlertType.SUSPECTED_ABDUCTION, region="Nord")
        hidden_road = self.add_alert("Road accident", AlertType.ROAD_ACCIDENT)
        unpublished = self.add_alert("Unpublished case", AlertType.MISSING_PERSON, status=AlertStatus.NEEDS_MODERATION)
        foreign = self.add_alert("Foreign case", AlertType.MISSING_PERSON, country="Gabon", region="Estuaire")

        response = self.client.get("/alerts")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Nadia Mbarga", response.data)
        self.assertIn(b"Jean Nfor", response.data)
        self.assertIn(b"Urgent abduction notice", response.data)
        self.assertNotIn(f"/alerts/{hidden_road.id}".encode(), response.data)
        self.assertNotIn(f"/alerts/{unpublished.id}".encode(), response.data)
        self.assertNotIn(f"/alerts/{foreign.id}".encode(), response.data)
        self.assertIn(f"/alerts/{centre_missing.id}".encode(), response.data)
        self.assertIn(f"/alerts/{followed_region_missing.id}".encode(), response.data)

    def test_feed_category_search_and_detail_access_use_the_same_targeting_rule(self) -> None:
        visible = self.add_alert("Nadia Mbarga", AlertType.MISSING_PERSON)
        hidden = self.add_alert("Road accident", AlertType.ROAD_ACCIDENT)

        filtered = self.client.get("/alerts?type=missing_person&q=nadia")
        self.assertIn(b"Nadia Mbarga", filtered.data)
        self.assertNotIn(f"/alerts/{hidden.id}".encode(), filtered.data)
        self.assertEqual(self.client.get(f"/alerts/{visible.id}").status_code, 200)
        self.assertEqual(self.client.get(f"/alerts/{hidden.id}").status_code, 404)

    def test_dashboard_uses_the_same_live_targeted_alert_source_as_the_full_feed(self) -> None:
        visible = self.add_alert("Nadia Mbarga", AlertType.MISSING_PERSON)
        hidden = self.add_alert("Road accident", AlertType.ROAD_ACCIDENT)

        dashboard = self.client.get("/dashboard")

        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Latest alerts", dashboard.data)
        self.assertIn(f"/alerts/{visible.id}".encode(), dashboard.data)
        self.assertNotIn(f"/alerts/{hidden.id}".encode(), dashboard.data)
        self.assertIn(b"View all alerts", dashboard.data)


if __name__ == "__main__":
    unittest.main()
