"""End-to-end Cameroon/Centre demonstration coverage for the multi-event MVP (T36)."""

from __future__ import annotations

import io
import tempfile
import unittest
from datetime import timedelta

from app import create_app
from app.extensions import db
from app.models import Alert, AlertPreference, AlertStatus, AlertType, Notification, User, utc_now


class MultiEventDemoJourneyTestCase(unittest.TestCase):
    """Exercise the public demo journey without requiring a live OpenAI key."""

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

        self.reporter = self.make_user("+237690000001", "Centre reporter", "Cameroon", "Centre")
        self.national_subscriber = self.make_user("+237690000002", "Littoral abduction subscriber", "Cameroon", "Littoral")
        self.centre_road_subscriber = self.make_user("+237690000003", "Centre road subscriber", "Cameroon", "Centre")
        self.littoral_road_subscriber = self.make_user("+237690000004", "Littoral road subscriber", "Cameroon", "Littoral")
        self.gabon_subscriber = self.make_user("+241660000005", "Gabon subscriber", "Gabon", "Estuaire")
        db.session.add_all(
            [
                self.reporter,
                self.national_subscriber,
                self.centre_road_subscriber,
                self.littoral_road_subscriber,
                self.gabon_subscriber,
            ]
        )
        db.session.add_all(
            [
                AlertPreference(user=self.national_subscriber, enabled_categories=["suspected_abduction"]),
                AlertPreference(user=self.centre_road_subscriber, enabled_categories=["road_accident"]),
                AlertPreference(user=self.littoral_road_subscriber, enabled_categories=["road_accident"]),
                AlertPreference(user=self.gabon_subscriber, enabled_categories=["suspected_abduction", "road_accident"]),
            ]
        )
        db.session.commit()
        self.client = self.app.test_client()
        self.sign_in_as(self.reporter)

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.upload_directory.cleanup()

    @staticmethod
    def make_user(phone: str, name: str, country: str, region: str) -> User:
        return User(
            phone_number=phone,
            display_name=name,
            country=country,
            primary_region=region,
            is_phone_verified=True,
        )

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    @staticmethod
    def valid_png() -> bytes:
        return b"\x89PNG\r\n\x1a\n" + b"save-us-demo-evidence"

    @staticmethod
    def abduction_form() -> dict[str, str]:
        return {
            "title": "Possible abduction near Mfoundi",
            "country": "Cameroon",
            "region": "Centre",
            "approximate_zone": "Mfoundi district, Yaounde",
            "abduction_at": "2026-07-19T16:30",
            "description": "Witnesses reported that a child was taken near the market.",
            "circumstances": "A vehicle left the area immediately afterwards.",
            "private_contact": "+237 690 000 001",
        }

    @staticmethod
    def road_accident_form() -> dict[str, str]:
        return {
            "title": "Collision on the N1 near Mbankomo",
            "country": "Cameroon",
            "region": "Centre",
            "approximate_zone": "N1, Mbankomo area",
            "manual_location": "N1 near Mbankomo market",
            "occurred_at": "2026-07-19T17:00",
            "latitude": "3.780000",
            "longitude": "11.380000",
            "victim_count": "2",
            "immediate_needs": "Ambulance and traffic support",
            "description": "Two vehicles collided and one lane is blocked.",
        }

    def notification_count(self, user: User, alert: Alert, kind: str) -> int:
        return db.session.scalar(
            db.select(db.func.count(Notification.id)).where(
                Notification.recipient_id == user.id,
                Notification.alert_id == alert.id,
                Notification.kind == kind,
            )
        )

    def test_cameroon_centre_multi_event_journey_targets_safely_and_expires_road_alert(self) -> None:
        """A national abduction and Centre road accident follow their distinct safety rules."""
        abduction_response = self.client.post(
            "/report/suspected-abduction",
            data={
                "action": "submit",
                **self.abduction_form(),
                "photo": (io.BytesIO(self.valid_png()), "evidence.png", "image/png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(abduction_response.status_code, 302)
        abduction = db.session.scalar(
            db.select(Alert).where(Alert.alert_type == AlertType.SUSPECTED_ABDUCTION)
        )
        self.assertEqual(abduction.status, AlertStatus.PUBLISHED)
        self.assertEqual((abduction.country, abduction.region), ("Cameroon", "Centre"))
        self.assertEqual(self.notification_count(self.national_subscriber, abduction, "alert_published"), 1)
        self.assertEqual(self.notification_count(self.gabon_subscriber, abduction, "alert_published"), 0)

        # Country-wide eligibility grants the Cameroon subscriber access, while an out-of-country user never gets the private media.
        self.sign_in_as(self.national_subscriber)
        eligible_photo = self.client.get(f"/alerts/{abduction.id}/photo")
        self.assertEqual(eligible_photo.status_code, 200)
        self.assertIn("private, no-store", eligible_photo.headers["Cache-Control"])
        eligible_photo.close()
        self.sign_in_as(self.gabon_subscriber)
        self.assertEqual(self.client.get(f"/alerts/{abduction.id}/photo").status_code, 404)

        self.sign_in_as(self.reporter)
        road_response = self.client.post(
            "/report/road-accident", data={"action": "submit", **self.road_accident_form()}
        )
        self.assertEqual(road_response.status_code, 302)
        road_accident = db.session.scalar(
            db.select(Alert).where(Alert.alert_type == AlertType.ROAD_ACCIDENT)
        )
        self.assertEqual(road_accident.status, AlertStatus.PUBLISHED)
        self.assertIsNotNone(road_accident.expires_at)
        self.assertEqual(self.notification_count(self.centre_road_subscriber, road_accident, "alert_published"), 1)
        self.assertEqual(self.notification_count(self.littoral_road_subscriber, road_accident, "alert_published"), 0)
        self.assertEqual(self.notification_count(self.gabon_subscriber, road_accident, "alert_published"), 0)

        # Expiry preserves the original Centre audience for the end-of-life update, then removes the accident from the public feed.
        road_accident.expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()
        self.sign_in_as(self.centre_road_subscriber)
        self.assertEqual(self.client.get("/dashboard").status_code, 200)
        self.assertEqual(db.session.get(Alert, road_accident.id).status, AlertStatus.EXPIRED)
        self.assertEqual(self.notification_count(self.centre_road_subscriber, road_accident, "alert_expired"), 1)
        self.assertEqual(self.notification_count(self.littoral_road_subscriber, road_accident, "alert_expired"), 0)
        self.assertEqual(self.client.get(f"/alerts/{road_accident.id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
