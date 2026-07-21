"""Tests for the public-safe alert-sheet contract (T49)."""

import json
import unittest
from datetime import timedelta

from app import create_app
from app.alert_sheet_contract import (
    ALERT_SHEET_SCHEMA_VERSION,
    ALERT_SHEET_SOURCE,
    AlertSheetSafetyError,
    build_alert_sheet,
    validate_alert_sheet,
)
from app.extensions import db
from app.models import Alert, AlertPreference, AlertStatus, AlertType, MissingPersonDetails, RoadAccidentDetails, User, utc_now


class AlertSheetContractTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.reporter = User(
            phone_number="+237692000001", country="Cameroon", primary_region="Centre", is_phone_verified=True,
        )
        db.session.add(self.reporter)
        db.session.commit()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def published_alert(self, alert_type: AlertType, *, title: str = "Community alert", summary: str = "A public-safe SAVE-US alert was published.") -> Alert:
        alert = Alert(
            reporter=self.reporter,
            alert_type=alert_type,
            status=AlertStatus.PUBLISHED,
            title=title,
            public_summary=summary,
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi district",
            published_at=utc_now() - timedelta(minutes=10),
        )
        db.session.add(alert)
        db.session.commit()
        return alert

    def test_contract_builds_a_safe_english_sheet_for_each_alert_type(self) -> None:
        for alert_type, expected_label in (
            (AlertType.MISSING_PERSON, "Missing person"),
            (AlertType.SUSPECTED_ABDUCTION, "Suspected abduction"),
            (AlertType.UNKNOWN_HOSPITAL_PATIENT, "Unknown hospital patient"),
            (AlertType.ROAD_ACCIDENT, "Road accident"),
        ):
            alert = self.published_alert(alert_type, title=f"{expected_label} alert")
            if alert_type == AlertType.ROAD_ACCIDENT:
                alert.expires_at = utc_now() + timedelta(hours=24)
                db.session.commit()
            sheet = build_alert_sheet(alert)
            self.assertEqual(sheet["schema_version"], ALERT_SHEET_SCHEMA_VERSION)
            self.assertEqual(sheet["category_label"], expected_label)
            self.assertEqual(sheet["status"], "published")
            self.assertEqual(sheet["source"], ALERT_SHEET_SOURCE)
            self.assertIn("Cameroon", sheet["approximate_location"])
            self.assertEqual(sheet["expires_at"] is not None, alert_type == AlertType.ROAD_ACCIDENT)
            self.assertEqual(validate_alert_sheet(sheet), sheet)

    def test_private_details_and_original_media_never_enter_the_contract(self) -> None:
        alert = self.published_alert(AlertType.MISSING_PERSON, title="Find Amadou")
        db.session.add(
            MissingPersonDetails(
                alert=alert,
                name="Amadou N.",
                last_seen_location="12 Rue de la Paix",
                private_family_contact="+237 692 111 222",
                circumstances="Private family circumstances.",
                photo_path="missing_person/private/amadou.png",
            )
        )
        db.session.commit()
        serialised_sheet = json.dumps(build_alert_sheet(alert))
        for private_value in ("12 Rue de la Paix", "+237 692 111 222", "Private family circumstances.", "missing_person/private/amadou.png"):
            self.assertNotIn(private_value, serialised_sheet)

        road = self.published_alert(AlertType.ROAD_ACCIDENT, title="N1 collision")
        db.session.add(
            RoadAccidentDetails(
                alert=road,
                manual_location="12 Avenue des Nations",
                latitude=3.848000,
                longitude=11.502000,
                media_references=["road_accident/private/collision.png"],
            )
        )
        db.session.commit()
        road_sheet = json.dumps(build_alert_sheet(road))
        self.assertNotIn("12 Avenue des Nations", road_sheet)
        self.assertNotIn("11.502", road_sheet)
        self.assertNotIn("road_accident/private/collision.png", road_sheet)

    def test_unsafe_public_text_is_blocked_and_unsafe_zone_falls_back_to_region(self) -> None:
        phone_summary = self.published_alert(
            AlertType.SUSPECTED_ABDUCTION,
            summary="Call +237 692 111 222 with information.",
        )
        with self.assertRaisesRegex(AlertSheetSafetyError, "contact number"):
            build_alert_sheet(phone_summary)

        coordinate_title = self.published_alert(
            AlertType.ROAD_ACCIDENT,
            title="Collision at 3.848000, 11.502000",
        )
        with self.assertRaisesRegex(AlertSheetSafetyError, "GPS"):
            build_alert_sheet(coordinate_title)

        zone_fallback = self.published_alert(AlertType.MISSING_PERSON)
        zone_fallback.approximate_zone = "12 Rue de la Paix"
        db.session.commit()
        sheet = build_alert_sheet(zone_fallback)
        self.assertEqual(sheet["approximate_location"], "Centre · Cameroon")

    def test_unpublished_alerts_and_tampered_payloads_are_rejected(self) -> None:
        alert = self.published_alert(AlertType.MISSING_PERSON)
        alert.status = AlertStatus.NEEDS_MODERATION
        db.session.commit()
        with self.assertRaisesRegex(AlertSheetSafetyError, "Only published"):
            build_alert_sheet(alert)

        published = self.published_alert(AlertType.MISSING_PERSON)
        payload = build_alert_sheet(published)
        payload["source"] = "Source: somebody else"
        with self.assertRaisesRegex(AlertSheetSafetyError, "attribution"):
            validate_alert_sheet(payload)


class AlertSheetRouteTestCase(unittest.TestCase):
    """Exercise the authorised printable HTML delivery layer (T50)."""

    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.reporter = User(phone_number="+237692000011", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        self.outsider = User(phone_number="+24174001000", country="Gabon", primary_region="Estuaire", is_phone_verified=True)
        self.alert = Alert(
            reporter=self.reporter,
            alert_type=AlertType.MISSING_PERSON,
            status=AlertStatus.PUBLISHED,
            title="Find Amadou",
            public_summary="A missing person alert was published for the Mfoundi district.",
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi district",
            published_at=utc_now(),
        )
        db.session.add_all([
            self.reporter,
            self.outsider,
            self.alert,
            AlertPreference(user=self.outsider, enabled_categories=["missing_person"]),
            MissingPersonDetails(
                alert=self.alert,
                private_family_contact="+237 692 333 444",
                last_seen_location="12 Rue de la Paix",
                photo_path="missing_person/private/amadou.png",
            ),
        ])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def test_authorised_reporter_receives_a4_printable_sheet_and_detail_action(self) -> None:
        self.sign_in_as(self.reporter)
        response = self.client.get(f"/alerts/{self.alert.id}/sheet")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Print alert sheet", response.data)
        self.assertIn(b"@page { size:A4", response.data)
        self.assertIn(b"Generated ", response.data)
        self.assertIn(b"Source: SAVE-US", response.data)
        self.assertNotIn(b"+237 692 333 444", response.data)
        self.assertNotIn(b"12 Rue de la Paix", response.data)
        self.assertNotIn(b"missing_person/private/amadou.png", response.data)
        detail = self.client.get(f"/alerts/{self.alert.id}")
        self.assertIn(f"/alerts/{self.alert.id}/sheet".encode(), detail.data)

    def test_unauthorised_or_unsafe_alert_sheets_are_not_generated(self) -> None:
        self.sign_in_as(self.outsider)
        self.assertEqual(self.client.get(f"/alerts/{self.alert.id}/sheet").status_code, 404)

        self.sign_in_as(self.reporter)
        self.alert.public_summary = "Call +237 692 333 444 immediately."
        db.session.commit()
        self.assertEqual(self.client.get(f"/alerts/{self.alert.id}/sheet").status_code, 404)


if __name__ == "__main__":
    unittest.main()
