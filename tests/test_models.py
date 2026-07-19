"""Regression tests for SAVE-US core entities."""

import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertPreference, AlertStatus, AlertType, User, UserRole


class CoreModelTestCase(unittest.TestCase):
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

    def test_user_preference_and_alert_relationships(self) -> None:
        user = User(
            phone_number="+237612345678",
            display_name="Amina N.",
            role=UserRole.REPORTER,
            is_phone_verified=True,
            country="Cameroon",
            primary_region="Centre",
        )
        preference = AlertPreference(
            user=user,
            enabled_categories=[AlertType.MISSING_PERSON.value],
            followed_regions=["Littoral"],
        )
        alert = Alert(
            reporter=user,
            alert_type=AlertType.MISSING_PERSON,
            title="Jean Bakary, 8",
            country="Cameroon",
            region="Centre",
            approximate_zone="Yaoundé area",
        )

        db.session.add_all([user, preference, alert])
        db.session.commit()

        saved_user = db.session.get(User, user.id)
        saved_alert = db.session.get(Alert, alert.id)
        self.assertEqual(saved_user.alert_preference.followed_regions, ["Littoral"])
        self.assertEqual(saved_alert.reporter.phone_number, "+237612345678")
        self.assertEqual(saved_alert.status, AlertStatus.DRAFT)
        self.assertEqual(saved_alert.alert_type, AlertType.MISSING_PERSON)


if __name__ == "__main__":
    unittest.main()
