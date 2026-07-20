"""Tests for the server-backed missing-person report form and drafts."""

import io
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import AIReview, Alert, AlertStatus, AlertType, MissingPersonDetails, User


class MissingPersonReportTestCase(unittest.TestCase):
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
        self.user = User(
            phone_number="+237611111111",
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
        self.upload_directory.cleanup()

    @staticmethod
    def valid_png() -> bytes:
        """Small PNG-signature payload; T12 verifies signatures, not image dimensions."""
        return b"\x89PNG\r\n\x1a\n" + b"save-us-demo-image"

    def test_save_draft_creates_and_resumes_missing_person_report(self) -> None:
        response = self.client.post(
            "/report/missing-person",
            data={
                "action": "save_draft",
                "name": "Jean Bakary",
                "age": "8",
                "sex": "male",
                "last_seen_at": "2026-07-18T16:30",
                "approximate_zone": "Mfoundi district, Yaoundé",
                "last_seen_location": "Near the primary school",
                "clothing_description": "Blue uniform",
                "private_family_contact": "+237 612 345 678",
                "circumstances": "Did not return home after school.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("saved=1", response.headers["Location"])

        alert = db.session.scalar(db.select(Alert))
        self.assertEqual((alert.alert_type, alert.status), (AlertType.MISSING_PERSON, AlertStatus.DRAFT))
        self.assertEqual((alert.country, alert.region), ("Cameroon", "Centre"))
        details = alert.missing_person_details
        self.assertEqual((details.name, details.age, details.sex), ("Jean Bakary", 8, "male"))
        self.assertEqual(details.private_family_contact, "+237 612 345 678")

        response = self.client.get(response.headers["Location"])
        self.assertIn(b"Draft saved", response.data)
        self.assertIn(b'value="Jean Bakary"', response.data)

    def test_save_draft_rejects_invalid_field_formats(self) -> None:
        response = self.client.post(
            "/report/missing-person",
            data={"action": "save_draft", "age": "126"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Age must be between 0 and 125", response.data)
        self.assertIsNone(db.session.scalar(db.select(Alert)))

    def test_review_validates_required_missing_person_fields_on_server(self) -> None:
        response = self.client.post(
            "/report/missing-person",
            data={"action": "review", "name": "Jean Bakary"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Age is required", response.data)
        self.assertIn(b"A photo is required", response.data)
        self.assertIn(b"Last-seen location is required", response.data)
        details = db.session.scalar(db.select(MissingPersonDetails))
        self.assertEqual(details.name, "Jean Bakary")
        self.assertEqual(details.alert.status, AlertStatus.DRAFT)

    def test_a_reporter_cannot_open_another_reporters_draft(self) -> None:
        other_user = User(
            phone_number="+237622222222",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        draft = Alert(
            reporter=other_user,
            alert_type=AlertType.MISSING_PERSON,
            title="Private draft",
            country="Cameroon",
            region="Centre",
        )
        db.session.add_all([other_user, draft])
        db.session.commit()

        response = self.client.get(f"/report/missing-person?draft={draft.id}")
        self.assertEqual(response.status_code, 404)

    def test_valid_photo_is_stored_privately_and_previewed_for_the_owner(self) -> None:
        response = self.client.post(
            "/report/missing-person",
            data={
                "action": "save_draft",
                "name": "Jean Bakary",
                "photo": (io.BytesIO(self.valid_png()), "jean.png", "image/png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        alert = db.session.scalar(db.select(Alert))
        photo_path = alert.missing_person_details.photo_path
        self.assertTrue(photo_path.startswith(f"missing_person/{alert.id}/"))
        self.assertTrue((Path(self.upload_directory.name) / photo_path).is_file())

        preview = self.client.get(f"/report/missing-person/{alert.id}/photo")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data, self.valid_png())
        self.assertIn("private, no-store", preview.headers["Cache-Control"])
        preview.close()

        report_page = self.client.get(response.headers["Location"])
        self.assertIn(b'data-has-stored-photo="true"', report_page.data)
        self.assertNotIn(b'name="photo" type="file" accept="image/png,image/jpeg,image/gif" required', report_page.data)

    def test_invalid_photo_is_rejected_without_creating_a_file(self) -> None:
        response = self.client.post(
            "/report/missing-person",
            data={
                "action": "save_draft",
                "photo": (io.BytesIO(b"not an image"), "unsafe.jpg", "image/jpeg"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"not a supported image", response.data)
        self.assertEqual(list(Path(self.upload_directory.name).rglob("*")), [])

    def test_photo_over_the_configured_size_limit_is_rejected(self) -> None:
        self.app.config["MAX_PHOTO_UPLOAD_BYTES"] = 10
        response = self.client.post(
            "/report/missing-person",
            data={
                "action": "save_draft",
                "photo": (io.BytesIO(self.valid_png()), "too-large.png", "image/png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"must be 5 MB or smaller", response.data)
        self.assertEqual(list(Path(self.upload_directory.name).rglob("*")), [])

    def test_complete_report_creates_a_persisted_ai_review_screen(self) -> None:
        response = self.client.post(
            "/report/missing-person",
            data={
                "action": "review",
                "name": "Jean Bakary",
                "age": "8",
                "sex": "male",
                "photo": (io.BytesIO(self.valid_png()), "jean.png", "image/png"),
                "last_seen_at": "2026-07-19T16:30",
                "approximate_zone": "Mfoundi district, Yaoundé",
                "last_seen_location": "Near the primary school",
                "clothing_description": "Blue school uniform",
                "private_family_contact": "+237 612 345 678",
                "circumstances": "Did not return home after school.",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/ai-review", response.headers["Location"])

        review = db.session.scalar(db.select(AIReview))
        self.assertEqual(review.decision, "publish_candidate")
        self.assertEqual(review.source, "deterministic_demo_fallback")
        screen = self.client.get(response.headers["Location"])
        self.assertEqual(screen.status_code, 200)
        self.assertIn(b"Public summary", screen.data)
        self.assertIn(b"Confidence score", screen.data)
        self.assertIn(b"Possible duplicates", screen.data)


if __name__ == "__main__":
    unittest.main()
