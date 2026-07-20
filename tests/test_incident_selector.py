"""Tests for the T25 unified incident-reporting entry point."""

import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertStatus, AlertType, User


class IncidentSelectorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"}
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(
            phone_number="+237655000000",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        db.session.add(self.user)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in(self) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = self.user.id

    def test_verified_user_can_choose_all_supported_citizen_incident_types(self) -> None:
        self.assertIn("/sign-in", self.client.get("/report").headers["Location"])
        self.sign_in()
        response = self.client.get("/report?type=road_accident")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Report an incident", response.data)
        self.assertIn(b"Missing person", response.data)
        self.assertIn(b"Suspected abduction", response.data)
        self.assertIn(b"Road accident", response.data)
        self.assertIn(b"/report/missing-person", response.data)
        self.assertIn(b"/report/suspected_abduction", response.data)
        self.assertIn(b"/report/road_accident", response.data)

    def test_road_accident_route_is_ready_and_does_not_create_a_draft_on_get(self) -> None:
        self.sign_in()
        before = db.session.scalar(db.select(db.func.count(Alert.id)))
        response = self.client.get("/report/road_accident")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Report road accident", response.data)
        self.assertEqual(db.session.scalar(db.select(db.func.count(Alert.id))), before)

    def test_missing_person_route_cannot_open_a_road_accident_draft(self) -> None:
        road_draft = Alert(
            reporter=self.user,
            alert_type=AlertType.ROAD_ACCIDENT,
            status=AlertStatus.DRAFT,
            title="Private road accident draft",
            country="Cameroon",
            region="Centre",
        )
        db.session.add(road_draft)
        db.session.commit()
        self.sign_in()
        self.assertEqual(self.client.get(f"/report/missing-person?draft={road_draft.id}").status_code, 404)


if __name__ == "__main__":
    unittest.main()
