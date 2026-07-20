"""Tests for CEMAC country, category, and regional recipient targeting."""

import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertPreference, AlertStatus, AlertType, User
from app.targeting import eligible_recipients, user_receives_alert


class TargetingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
            }
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.reporter = self.add_user("Reporter", "Cameroon", "Centre", ["missing_person"])

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def add_user(self, name, country, region, categories, followed_regions=None, verified=True):
        user = User(
            phone_number=f"+2376000000{db.session.scalar(db.select(db.func.count(User.id))) + 1:02d}",
            display_name=name,
            country=country,
            primary_region=region,
            is_phone_verified=verified,
        )
        preference = AlertPreference(
            user=user,
            enabled_categories=categories,
            followed_regions=followed_regions or [],
        )
        db.session.add_all([user, preference])
        db.session.commit()
        return user

    def published_alert(self, alert_type, country="Cameroon", region="Centre"):
        alert = Alert(
            reporter=self.reporter,
            alert_type=alert_type,
            status=AlertStatus.PUBLISHED,
            title="Targeting test alert",
            country=country,
            region=region,
        )
        db.session.add(alert)
        db.session.commit()
        return alert

    def test_missing_person_targets_matching_country_category_and_regions(self) -> None:
        primary_region = self.add_user("Centre subscriber", "Cameroon", "Centre", ["missing_person"])
        followed_region = self.add_user("Follower", "Cameroon", "Littoral", ["missing_person"], ["Centre"])
        wrong_region = self.add_user("Other region", "Cameroon", "Littoral", ["missing_person"])
        category_opt_out = self.add_user("Category opt out", "Cameroon", "Centre", ["road_accident"])
        another_country = self.add_user("Gabon subscriber", "Gabon", "Estuaire", ["missing_person"])
        alert = self.published_alert(AlertType.MISSING_PERSON)

        recipients = eligible_recipients(alert, [primary_region, followed_region, wrong_region, category_opt_out, another_country])

        self.assertEqual([user.id for user in recipients], [primary_region.id, followed_region.id])

    def test_abduction_is_country_wide_but_still_respects_category_opt_out(self) -> None:
        distant_region = self.add_user("Distant subscriber", "Cameroon", "Littoral", ["suspected_abduction"])
        category_opt_out = self.add_user("Category opt out", "Cameroon", "Centre", ["missing_person"])
        another_country = self.add_user("Chad subscriber", "Chad", "N'Djamena", ["suspected_abduction"])
        alert = self.published_alert(AlertType.SUSPECTED_ABDUCTION, region="Centre")

        recipients = eligible_recipients(alert, [distant_region, category_opt_out, another_country])

        self.assertEqual([user.id for user in recipients], [distant_region.id])

    def test_unpublished_or_unverified_users_are_never_targeted(self) -> None:
        subscriber = self.add_user("Unverified subscriber", "Cameroon", "Centre", ["missing_person"], verified=False)
        alert = self.published_alert(AlertType.MISSING_PERSON)
        self.assertFalse(user_receives_alert(subscriber, alert))

        alert.status = AlertStatus.NEEDS_MODERATION
        self.assertFalse(user_receives_alert(self.reporter, alert))


if __name__ == "__main__":
    unittest.main()
