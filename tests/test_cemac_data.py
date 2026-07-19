"""Tests for CEMAC reference data and the idempotent demo seed."""

import unittest

from app import create_app
from app.cemac import country_options, subdivisions_for
from app.extensions import db
from app.models import AlertPreference, User
from app.seed import DEMO_USERS, seed_demo_data


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
