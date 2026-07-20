"""Tests for the dedicated suspected-abduction report workflow (T27)."""

import io
import tempfile
import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertStatus, AlertType, SuspectedAbductionDetails, User


class SuspectedAbductionReportTestCase(unittest.TestCase):
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
            phone_number="+237633000000",
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
        return b"\x89PNG\r\n\x1a\n" + b"save-us-abduction-image"

    def form_data(self) -> dict[str, str]:
        return {
            "title": "Possible abduction near Mfoundi",
            "country": "Cameroon",
            "region": "Centre",
            "approximate_zone": "Mfoundi district, Yaoundé",
            "abduction_at": "2026-07-19T16:30",
            "description": "Witnesses reported that a child was taken near the market.",
            "circumstances": "A vehicle left the area immediately afterwards.",
            "private_contact": "+237 633 000 000",
        }

    def test_save_and_resume_an_abduction_draft_without_a_photo(self) -> None:
        response = self.client.post(
            "/report/suspected-abduction",
            data={"action": "save_draft", **self.form_data()},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("saved=1", response.headers["Location"])
        alert = db.session.scalar(db.select(Alert))
        self.assertEqual((alert.alert_type, alert.status), (AlertType.SUSPECTED_ABDUCTION, AlertStatus.DRAFT))
        self.assertEqual((alert.country, alert.region), ("Cameroon", "Centre"))
        self.assertIsNone(alert.suspected_abduction_details.photo_path)

        resumed = self.client.get(response.headers["Location"])
        self.assertIn(b"Possible abduction near Mfoundi", resumed.data)
        self.assertNotIn(b"A recent photo is required", resumed.data)

    def test_validates_an_optional_photo_and_keeps_it_private(self) -> None:
        response = self.client.post(
            "/report/suspected-abduction",
            data={
                "action": "save_draft",
                **self.form_data(),
                "photo": (io.BytesIO(self.valid_png()), "evidence.png", "image/png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        alert = db.session.scalar(db.select(Alert))
        details = alert.suspected_abduction_details
        self.assertTrue(details.photo_path.startswith("suspected_abduction/"))
        preview = self.client.get(f"/report/suspected-abduction/{alert.id}/photo")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.data, self.valid_png())
        self.assertIn("private, no-store", preview.headers["Cache-Control"])
        preview.close()

    def test_rejects_an_invalid_optional_photo(self) -> None:
        response = self.client.post(
            "/report/suspected-abduction",
            data={
                "action": "save_draft",
                **self.form_data(),
                "photo": (io.BytesIO(b"not an image"), "evidence.png", "image/png"),
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"not a supported image", response.data)
        self.assertIsNone(db.session.scalar(db.select(Alert)))

    def test_submit_uses_plain_language_and_queues_the_category_for_later_review(self) -> None:
        response = self.client.post(
            "/report/suspected-abduction",
            data={"action": "submit", **self.form_data()},
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/submitted", response.headers["Location"])
        alert = db.session.scalar(db.select(Alert))
        self.assertEqual(alert.status, AlertStatus.AI_REVIEW)
        self.assertEqual(self.client.get(response.headers["Location"]).status_code, 200)
        self.assertIn(b"Your report has been received", self.client.get(response.headers["Location"]).data)

    def test_missing_person_form_cannot_resume_an_abduction_draft(self) -> None:
        draft = Alert(
            reporter=self.user,
            alert_type=AlertType.SUSPECTED_ABDUCTION,
            status=AlertStatus.DRAFT,
            title="Private abduction draft",
            country="Cameroon",
            region="Centre",
        )
        db.session.add_all([draft, SuspectedAbductionDetails(alert=draft)])
        db.session.commit()
        self.assertEqual(self.client.get(f"/report/missing-person?draft={draft.id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
