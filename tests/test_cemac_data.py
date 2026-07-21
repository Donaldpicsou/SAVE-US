"""Tests for CEMAC reference data and the idempotent demo seed."""

import unittest

from app import create_app
from app.cemac import country_options, subdivisions_for
from app.extensions import db
from app.models import (
    Alert,
    AlertPreference,
    AlertStatus,
    AlertType,
    HospitalVerificationRequest,
    ModeratorAccessRequest,
    Notification,
    User,
)
from app.seed import DEMO_ALERT_IDS, DEMO_HOSPITAL_REQUEST_ID, DEMO_MODERATOR_REQUEST_ID, DEMO_USERS, seed_demo_data


class CemacDataTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_reference_data_has_six_countries_and_cameroon_regions(self) -> None:
        countries = country_options()
        self.assertEqual(len(countries), 6)
        self.assertIn({"code": "cameroun", "name": "Cameroon"}, countries)
        self.assertEqual(len(subdivisions_for("cameroun")), 10)
        self.assertEqual(subdivisions_for("unknown"), [])

    def test_demo_seed_is_idempotent(self) -> None:
        self.assertEqual(seed_demo_data(), (len(DEMO_USERS), len(DEMO_USERS)))
        self.assertEqual(seed_demo_data(), (0, 0))
        self.assertEqual(db.session.scalar(db.select(db.func.count(User.id))), len(DEMO_USERS))
        self.assertEqual(
            db.session.scalar(db.select(db.func.count(AlertPreference.id))),
            len(DEMO_USERS),
        )
        self.assertEqual(db.session.scalar(db.select(db.func.count(Alert.id))), 4)
        self.assertEqual(
            db.session.get(Alert, DEMO_ALERT_IDS["missing"]).status,
            AlertStatus.PUBLISHED,
        )
        self.assertTrue(db.session.get(Alert, DEMO_ALERT_IDS["missing"]).missing_person_details.photo_path)
        self.assertTrue(db.session.get(Alert, DEMO_ALERT_IDS["missing"]).missing_person_details.public_media_authorized)
        self.assertEqual(
            db.session.get(Alert, DEMO_ALERT_IDS["abduction"]).alert_type,
            AlertType.SUSPECTED_ABDUCTION,
        )
        self.assertEqual(
            db.session.get(Alert, DEMO_ALERT_IDS["road_accident"]).status,
            AlertStatus.PUBLISHED,
        )
        self.assertEqual(
            db.session.get(Alert, DEMO_ALERT_IDS["moderation"]).status,
            AlertStatus.NEEDS_MODERATION,
        )
        self.assertIsNotNone(db.session.get(HospitalVerificationRequest, DEMO_HOSPITAL_REQUEST_ID))
        self.assertIsNotNone(db.session.get(ModeratorAccessRequest, DEMO_MODERATOR_REQUEST_ID))
        self.assertGreater(db.session.scalar(db.select(db.func.count(Notification.id))), 0)
