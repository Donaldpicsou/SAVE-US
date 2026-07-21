"""End-to-end safety regression coverage for printable sheets and sharing (T54)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, quote, urlparse

from PIL import Image
from pypdf import PdfReader

from app import create_app
from app.extensions import db
from app.models import Alert, AlertShareLink, AlertStatus, AlertType, MissingPersonDetails, User, utc_now


class AlertSheetSharingEndToEndTestCase(unittest.TestCase):
    """One complete authorised-to-public sharing path must remain data-minimised."""

    private_values = (
        "+237 692 777 888",
        "12 Rue de la Paix",
        "Private family circumstances.",
        "missing_person/private/amadou-original.png",
    )

    def setUp(self) -> None:
        self.upload_directory = tempfile.TemporaryDirectory()
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://", "UPLOAD_FOLDER": self.upload_directory.name})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.reporter = User(
            phone_number="+237692000031", display_name="Amadou's family", country="Cameroon",
            primary_region="Centre", is_phone_verified=True,
        )
        self.alert = Alert(
            reporter=self.reporter, alert_type=AlertType.MISSING_PERSON, status=AlertStatus.PUBLISHED,
            title="Help locate Amadou N.",
            public_summary="A missing person alert has been published for the Mfoundi district.",
            country="Cameroon", region="Centre", approximate_zone="Mfoundi district", published_at=utc_now(),
        )
        db.session.add_all([
            self.reporter,
            self.alert,
            MissingPersonDetails(
                alert=self.alert, name="Amadou N.", last_seen_location=self.private_values[1],
                private_family_contact=self.private_values[0], circumstances=self.private_values[2],
                photo_path=self.private_values[3],
            ),
        ])
        db.session.commit()
        self.client = self.app.test_client()
        self.sign_in_as(self.reporter)

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.upload_directory.cleanup()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def assert_no_private_values(self, content: str | bytes) -> None:
        content = content.decode("utf-8") if isinstance(content, bytes) else content
        for value in self.private_values:
            self.assertNotIn(value, content)

    def test_print_pdf_share_and_revocation_use_only_the_english_safe_contract(self) -> None:
        # Printable HTML: English, attributed, A4-ready, and stripped of report-private data.
        html = self.client.get(f"/alerts/{self.alert.id}/sheet")
        self.assertEqual(html.status_code, 200)
        for expected in (b"Print alert sheet", b"Missing person", b"Safety guidance", b"Source: SAVE-US", b"@page { size:A4"):
            self.assertIn(expected, html.data)
        self.assert_no_private_values(html.data)

        # Downloaded PDF: extract text to verify public content and private-data exclusion.
        pdf_response = self.client.get(f"/alerts/{self.alert.id}/sheet.pdf")
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response.mimetype, "application/pdf")
        pdf_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(pdf_response.data)).pages)
        for expected in ("SAVE-US", "MISSING PERSON", "APPROXIMATE AREA", "SAFETY GUIDANCE", "Source: SAVE-US"):
            self.assertIn(expected, pdf_text)
        self.assert_no_private_values(pdf_text)
        self.assertEqual(pdf_response.headers["Cache-Control"], "private, no-store, max-age=0")

        # Share URL: opaque, anonymous, and rendered with no original media.
        issued = self.client.post(f"/alerts/{self.alert.id}/share-links")
        self.assertEqual(issued.status_code, 200)
        share_payload = issued.get_json()
        secure_url = share_payload["url"]
        secure_path = urlparse(secure_url).path
        self.assertRegex(secure_path, r"^/s/[A-Za-z0-9_-]{30,}$")
        self.assertNotIn(self.alert.id, secure_path)
        link = db.session.scalar(db.select(AlertShareLink).where(AlertShareLink.alert_id == self.alert.id))
        self.assertIsNotNone(link)

        with self.client.session_transaction() as browser_session:
            browser_session.clear()
        shared_page = self.client.get(secure_path)
        self.assertEqual(shared_page.status_code, 200)
        self.assertIn(b"Source: SAVE-US", shared_page.data)
        self.assertIn(b"Missing person", shared_page.data)
        self.assertNotIn(b"<img", shared_page.data)
        self.assert_no_private_values(shared_page.data)

        # WhatsApp payload: the complete public incident summary and opaque URL only.
        script = (Path(self.app.static_folder) / "js" / "alert-share.js").read_text(encoding="utf-8")
        self.assertIn('window.open("about:blank", "_blank")', script)
        self.assertIn("https://wa.me/?text=${encodeURIComponent(payload.whatsapp_text)}", script)
        self.assertIn("*SAVE-US Emergency Alert*", share_payload["whatsapp_text"])
        self.assertIn("*Category:* Missing person", share_payload["whatsapp_text"])
        self.assertIn(f"*Alert:* {self.alert.title}", share_payload["whatsapp_text"])
        self.assertIn(f"*Summary:*\n{self.alert.public_summary}", share_payload["whatsapp_text"])
        self.assertIn("*Approximate area:* Mfoundi district · Centre · Cameroon", share_payload["whatsapp_text"])
        self.assertIn(f"*Secure link:* {secure_url}", share_payload["whatsapp_text"])
        whatsapp_url = f"https://wa.me/?text={quote(share_payload['whatsapp_text'], safe='')}"
        whatsapp_payload = parse_qs(urlparse(whatsapp_url).query)["text"][0]
        self.assertEqual(whatsapp_payload, share_payload["whatsapp_text"])
        self.assertIn(secure_url, whatsapp_payload)
        self.assert_no_private_values(whatsapp_payload)

        # Dynamic values cannot inject WhatsApp emphasis, strike-through, or code styling.
        self.alert.title = "Help *locate* _Amadou_"
        self.alert.public_summary = "Do not ~alter~ `this` report."
        db.session.commit()
        self.sign_in_as(self.reporter)
        sanitised_payload = self.client.post(f"/alerts/{self.alert.id}/share-links").get_json()["whatsapp_text"]
        self.assertIn("*Alert:* Help locate Amadou", sanitised_payload)
        self.assertIn("*Summary:*\nDo not alter this report.", sanitised_payload)
        self.assertNotIn("*locate*", sanitised_payload)
        self.assertNotIn("~alter~", sanitised_payload)
        self.assertNotIn("`this`", sanitised_payload)

        # Revocation: the formerly valid anonymous link is immediately unavailable.
        self.sign_in_as(self.reporter)
        revoked = self.client.post(f"/alerts/{self.alert.id}/share-links/{link.id}/revoke")
        self.assertEqual(revoked.status_code, 204)
        self.assertIsNotNone(db.session.get(AlertShareLink, link.id).revoked_at)
        with self.client.session_transaction() as browser_session:
            browser_session.clear()
        self.assertEqual(self.client.get(secure_path).status_code, 404)

    def test_explicitly_authorised_identification_photo_uses_a_safe_derivative_everywhere(self) -> None:
        original = Path(self.app.config["UPLOAD_FOLDER"]) / self.private_values[3]
        original.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1800, 1200), color=(220, 90, 30)).save(original, format="PNG")
        self.alert.missing_person_details.public_media_authorized = True
        db.session.commit()

        sheet = self.client.get(f"/alerts/{self.alert.id}/sheet")
        self.assertEqual(sheet.status_code, 200)
        self.assertIn(f'/alerts/{self.alert.id}/sheet-image'.encode(), sheet.data)
        self.assertNotIn(self.private_values[3].encode(), sheet.data)

        pdf = self.client.get(f"/alerts/{self.alert.id}/sheet.pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertIn(b"/Subtype /Image", pdf.data)

        issued = self.client.post(f"/alerts/{self.alert.id}/share-links").get_json()
        secure_path = urlparse(issued["url"]).path
        with self.client.session_transaction() as browser_session:
            browser_session.clear()
        shared_page = self.client.get(secure_path)
        self.assertEqual(shared_page.status_code, 200)
        self.assertIn(f'{secure_path}/image'.encode(), shared_page.data)
        self.assertIn(b'property="og:image"', shared_page.data)
        self.assertNotIn(self.private_values[3].encode(), shared_page.data)

        derivative = self.client.get(f"{secure_path}/image")
        self.assertEqual(derivative.status_code, 200)
        self.assertEqual(derivative.mimetype, "image/jpeg")
        image = Image.open(BytesIO(derivative.data))
        self.assertEqual(image.format, "JPEG")
        self.assertFalse(image.getexif())

        link = db.session.scalar(db.select(AlertShareLink).where(AlertShareLink.alert_id == self.alert.id))
        self.sign_in_as(self.reporter)
        self.assertEqual(self.client.post(f"/alerts/{self.alert.id}/share-links/{link.id}/revoke").status_code, 204)
        with self.client.session_transaction() as browser_session:
            browser_session.clear()
        self.assertEqual(self.client.get(f"{secure_path}/image").status_code, 404)


if __name__ == "__main__":
    unittest.main()
