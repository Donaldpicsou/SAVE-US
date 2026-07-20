"""Tests for the mobile-friendly road-accident report workflow (T31)."""

import io
import tempfile
import unittest
from datetime import timedelta

from app import create_app
from app.extensions import db
from app.models import Alert, AlertPreference, AlertStatus, AlertType, ReportAction, RoadAccidentDetails, User, utc_now
from app.road_media_moderation import MEDIA_STATUS_BLOCKED, review_road_accident_media


class RoadAccidentReportTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.upload_directory = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "UPLOAD_FOLDER": self.upload_directory.name,
        })
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(phone_number="+237633000000", country="Cameroon", primary_region="Littoral", is_phone_verified=True)
        self.other_user = User(phone_number="+237634000000", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        db.session.add_all([self.user, self.other_user])
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = self.user.id

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.upload_directory.cleanup()

    @staticmethod
    def valid_png() -> bytes:
        return b"\x89PNG\r\n\x1a\n" + b"save-us-road-accident-image"

    def form_data(self) -> dict[str, str]:
        return {
            "title": "Collision on the N3 near Dibamba",
            "country": "Cameroon",
            "region": "Littoral",
            "approximate_zone": "N3, Dibamba area",
            "manual_location": "N3 near the Dibamba toll station",
            "occurred_at": "2026-07-19T16:30",
            "latitude": "4.200100",
            "longitude": "9.775300",
            "victim_count": "2",
            "immediate_needs": "Ambulance and traffic support",
            "description": "Two vehicles collided and one lane is blocked.",
        }

    def test_save_resume_and_keep_optional_photo_private(self) -> None:
        response = self.client.post(
            "/report/road-accident",
            data={
                "action": "save_draft", **self.form_data(),
                "photo": (io.BytesIO(self.valid_png()), "collision.png", "image/png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        alert = db.session.scalar(db.select(Alert))
        self.assertEqual((alert.alert_type, alert.status), (AlertType.ROAD_ACCIDENT, AlertStatus.DRAFT))
        self.assertEqual(alert.road_accident_details.victim_count, 2)
        self.assertEqual(len(alert.road_accident_details.media_references), 1)
        self.assertIn(b"Collision on the N3 near Dibamba", self.client.get(response.headers["Location"]).data)

        preview = self.client.get(f"/report/road-accident/{alert.id}/photo")
        self.assertEqual(preview.status_code, 200)
        self.assertIn("private, no-store", preview.headers["Cache-Control"])
        preview.close()
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = self.other_user.id
        self.assertEqual(self.client.get(f"/report/road-accident/{alert.id}/photo").status_code, 404)

    def test_submit_queues_complete_report_and_validates_coordinate_pairs(self) -> None:
        invalid = self.form_data()
        invalid.pop("longitude")
        response = self.client.post("/report/road-accident", data={"action": "submit", **invalid})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Latitude and longitude must be provided together", response.data)

        response = self.client.post("/report/road-accident", data={"action": "submit", **self.form_data()})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/submitted", response.headers["Location"])
        alert = db.session.scalar(db.select(Alert).where(Alert.alert_type == AlertType.ROAD_ACCIDENT))
        self.assertEqual(alert.status, AlertStatus.PUBLISHED)
        self.assertIsNotNone(alert.published_at)
        self.assertIsNotNone(alert.expires_at)
        self.assertEqual(alert.expires_at - alert.published_at, timedelta(hours=24))
        self.assertEqual(self.client.get(response.headers["Location"]).status_code, 200)

    def test_published_accident_targets_the_affected_region_then_expires(self) -> None:
        subscriber = User(phone_number="+237635000000", country="Cameroon", primary_region="Littoral", is_phone_verified=True)
        db.session.add_all([subscriber, AlertPreference(user=subscriber, enabled_categories=["road_accident"])])
        db.session.commit()
        response = self.client.post("/report/road-accident", data={"action": "submit", **self.form_data()})
        alert = db.session.scalar(db.select(Alert).where(Alert.alert_type == AlertType.ROAD_ACCIDENT))
        self.assertEqual(alert.status, AlertStatus.PUBLISHED)
        self.assertEqual(len(subscriber.notifications), 1)
        self.assertIn(b"shared with eligible people", self.client.get(response.headers["Location"]).data)

        alert.expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()
        self.client.get("/dashboard")
        self.assertEqual(db.session.get(Alert, alert.id).status, AlertStatus.EXPIRED)

    def test_reporter_can_close_a_published_accident_with_a_reasoned_audit_record(self) -> None:
        self.client.post("/report/road-accident", data={"action": "submit", **self.form_data()})
        alert = db.session.scalar(db.select(Alert).where(Alert.alert_type == AlertType.ROAD_ACCIDENT))
        response = self.client.post(
            f"/reports/{alert.id}/close",
            data={"action": "closed", "reason": "Emergency services cleared the road."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(db.session.get(Alert, alert.id).status, AlertStatus.WITHDRAWN)
        action = db.session.scalar(db.select(ReportAction).where(ReportAction.alert_id == alert.id))
        self.assertEqual((action.action, action.reason), ("closed", "Emergency services cleared the road."))

    def test_submitted_photo_enters_moderation_when_live_visual_review_is_unavailable(self) -> None:
        response = self.client.post(
            "/report/road-accident",
            data={
                "action": "submit", **self.form_data(),
                "photo": (io.BytesIO(self.valid_png()), "collision.png", "image/png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        alert = db.session.scalar(db.select(Alert).where(Alert.alert_type == AlertType.ROAD_ACCIDENT))
        self.assertEqual(alert.status, AlertStatus.NEEDS_MODERATION)
        self.assertEqual(alert.road_accident_media_review.status, "needs_moderation")
        submitted = self.client.get(response.headers["Location"])
        self.assertIn(b"needs a safety check", submitted.data)

    def test_server_blocks_a_missing_or_tampered_stored_media_reference(self) -> None:
        alert = Alert(
            reporter=self.user, alert_type=AlertType.ROAD_ACCIDENT, status=AlertStatus.AI_REVIEW,
            title="Tampered photo", country="Cameroon", region="Littoral",
        )
        details = RoadAccidentDetails(alert=alert, media_references=["road_accident/missing/photo.jpg"])
        db.session.add_all([alert, details])
        db.session.commit()
        result = review_road_accident_media(
            alert, upload_root=self.upload_directory.name, max_bytes=5 * 1024 * 1024,
            api_key=None, model="gpt-5.6", timeout=1,
        )
        self.assertEqual(result.status, MEDIA_STATUS_BLOCKED)
        self.assertIn("could not pass", result.reason)


if __name__ == "__main__":
    unittest.main()
