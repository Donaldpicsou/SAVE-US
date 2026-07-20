"""Regression tests for SAVE-US core entities."""

import unittest
from datetime import timedelta

from app import create_app
from app.extensions import db
from app.models import (
    Alert,
    AlertPreference,
    AlertStatus,
    AlertType,
    MissingPersonDetails,
    MissingPersonSex,
    RoadAccidentDetails,
    SuspectedAbductionDetails,
    User,
    UserRole,
    utc_now,
)


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

    def test_missing_person_rules_identify_required_fields_and_complete_details(self) -> None:
        user = User(
            phone_number="+237699999999",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        alert = Alert(
            reporter=user,
            alert_type=AlertType.MISSING_PERSON,
            title="Draft missing-person report",
            country="Cameroon",
            region="Centre",
        )
        details = MissingPersonDetails(alert=alert)
        db.session.add_all([user, alert, details])
        db.session.commit()

        self.assertEqual(
            set(details.validation_errors()),
            {"name", "age", "sex", "photo", "last_seen_at", "last_seen_location", "private_family_contact"},
        )
        self.assertFalse(details.is_submission_ready)

        details.name = "Jean Bakary"
        details.age = 8
        details.sex = MissingPersonSex.MALE.value
        details.photo_path = "uploads/jean-bakary.jpg"
        details.last_seen_at = utc_now() - timedelta(hours=2)
        details.last_seen_location = "Mfoundi district, Yaoundé"
        details.clothing_description = "Blue school uniform and red backpack"
        details.private_family_contact = "+237 612 345 678"
        details.circumstances = "Did not return home after school."
        db.session.commit()

        self.assertEqual(details.validation_errors(), {})
        self.assertTrue(details.is_submission_ready)
        self.assertEqual(db.session.get(Alert, alert.id).missing_person_details.name, "Jean Bakary")

    def test_missing_person_rules_reject_future_last_seen_date(self) -> None:
        details = MissingPersonDetails(last_seen_at=utc_now() + timedelta(minutes=1))
        self.assertEqual(
            details.validation_errors()["last_seen_at"],
            "Last-seen date and time cannot be in the future.",
        )

    def test_abduction_details_are_isolated_and_validate_required_evidence(self) -> None:
        user = User(
            phone_number="+237688888888",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        alert = Alert(
            reporter=user,
            alert_type=AlertType.SUSPECTED_ABDUCTION,
            title="Possible abduction near Mfoundi",
            country="Cameroon",
            region="Centre",
        )
        details = SuspectedAbductionDetails(alert=alert)
        db.session.add_all([user, alert, details])
        db.session.commit()

        self.assertEqual(
            set(details.validation_errors()),
            {"abduction_at", "approximate_zone", "description", "circumstances", "private_contact"},
        )
        self.assertFalse(details.is_submission_ready)

        alert.approximate_zone = "Mfoundi district, Yaoundé"
        details.abduction_at = utc_now() - timedelta(hours=1)
        details.description = "A child was reportedly taken from the market area."
        details.circumstances = "Witnesses reported a vehicle leaving the area immediately afterwards."
        details.private_contact = "+237 688 888 888"
        db.session.commit()

        self.assertEqual(details.validation_errors(), {})
        self.assertTrue(details.is_submission_ready)
        self.assertIsNone(details.photo_path)
        self.assertIs(db.session.get(Alert, alert.id).suspected_abduction_details, details)

    def test_abduction_details_reject_future_event_time_and_wrong_alert_type(self) -> None:
        missing_alert = Alert(
            reporter=User(
                phone_number="+237677777777",
                country="Cameroon",
                primary_region="Centre",
                is_phone_verified=True,
            ),
            alert_type=AlertType.MISSING_PERSON,
            title="Wrong category",
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi",
        )
        details = SuspectedAbductionDetails(
            alert=missing_alert,
            photo_path="uploads/photo.jpg",
            abduction_at=utc_now() + timedelta(minutes=1),
            description="Description",
            circumstances="Circumstances",
            private_contact="+237 677 777 777",
        )
        errors = details.validation_errors()
        self.assertEqual(errors["alert_type"], "Abduction details require a suspected-abduction alert.")
        self.assertEqual(errors["abduction_at"], "Abduction date and time cannot be in the future.")

    def test_road_accident_details_keep_private_operational_data_and_validate_submission_rules(self) -> None:
        user = User(
            phone_number="+237666666666", country="Cameroon", primary_region="Littoral", is_phone_verified=True,
        )
        alert = Alert(
            reporter=user, alert_type=AlertType.ROAD_ACCIDENT, title="Collision near Dibamba",
            country="Cameroon", region="Littoral",
        )
        details = RoadAccidentDetails(alert=alert)
        db.session.add_all([user, alert, details])
        db.session.commit()

        self.assertEqual(
            set(details.validation_errors()),
            {"occurred_at", "manual_location", "affected_region", "description"},
        )
        details.occurred_at = utc_now() - timedelta(minutes=20)
        details.manual_location = "N3 road near Dibamba toll station"
        details.affected_region = "Littoral"
        details.latitude = 4.2001
        details.longitude = 9.7753
        details.victim_count = 2
        details.immediate_needs = "Ambulance and traffic support requested."
        details.description = "Two vehicles collided and one lane is blocked."
        details.media_references = ["road_accident/alert-1/photo.jpg"]
        db.session.commit()

        self.assertEqual(details.validation_errors(), {})
        self.assertTrue(details.is_submission_ready)
        saved = db.session.get(Alert, alert.id).road_accident_details
        self.assertEqual(saved.victim_count, 2)
        self.assertEqual(saved.media_references, ["road_accident/alert-1/photo.jpg"])

    def test_road_accident_details_reject_invalid_coordinates_and_category(self) -> None:
        alert = Alert(
            reporter=User(phone_number="+237655555555", country="Cameroon", primary_region="Centre", is_phone_verified=True),
            alert_type=AlertType.MISSING_PERSON, title="Wrong category", country="Cameroon", region="Centre",
        )
        details = RoadAccidentDetails(
            alert=alert, occurred_at=utc_now() + timedelta(minutes=1), manual_location="Mfoundi",
            affected_region="Littoral", latitude=4.0, victim_count=-1, description="Collision",
        )
        errors = details.validation_errors()
        self.assertEqual(errors["alert_type"], "Road-accident details require a road-accident alert.")
        self.assertEqual(errors["occurred_at"], "Accident date and time cannot be in the future.")
        self.assertEqual(errors["affected_region"], "The affected region must match the alert region.")
        self.assertEqual(errors["coordinates"], "Latitude and longitude must be provided together.")
        self.assertEqual(errors["victim_count"], "Victim count cannot be negative.")


if __name__ == "__main__":
    unittest.main()
