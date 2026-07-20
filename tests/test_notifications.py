"""Tests for persisted, targeted notification delivery and read-state controls."""

import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertPreference, AlertStatus, AlertType, Notification, User
from app.notification_service import queue_closure_notifications, queue_review_outcome_notifications
from app.targeting import eligible_recipients


class NotificationTestCase(unittest.TestCase):
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
        self.reporter = User(
            phone_number="+237699000001",
            display_name="Reporter",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        self.recipient = User(
            phone_number="+237699000002",
            display_name="Recipient",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        self.opted_out = User(
            phone_number="+237699000003",
            display_name="Different preference",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        db.session.add_all(
            [
                self.reporter,
                self.recipient,
                self.opted_out,
                AlertPreference(user=self.reporter, enabled_categories=["missing_person"]),
                AlertPreference(
                    user=self.recipient,
                    enabled_categories=["missing_person"],
                    email_notifications_enabled=True,
                ),
                AlertPreference(user=self.opted_out, enabled_categories=["road_accident"]),
            ]
        )
        db.session.flush()
        self.alert = Alert(
            reporter=self.reporter,
            alert_type=AlertType.MISSING_PERSON,
            status=AlertStatus.PUBLISHED,
            title="Find Amadou",
            public_summary="A child needs help returning home.",
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi",
        )
        db.session.add(self.alert)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def test_publication_only_notifies_targeted_subscriber_and_reporter(self) -> None:
        queue_review_outcome_notifications(self.alert)
        db.session.commit()

        recipient_notifications = db.session.scalars(
            db.select(Notification).where(Notification.recipient_id == self.recipient.id)
        ).all()
        self.assertEqual(len(recipient_notifications), 1)
        self.assertEqual(recipient_notifications[0].kind, "alert_published")
        self.assertEqual(recipient_notifications[0].email_delivery_status, "simulated_sent")
        self.assertEqual(
            db.session.scalar(db.select(db.func.count(Notification.id)).where(Notification.recipient_id == self.opted_out.id)),
            0,
        )
        self.assertEqual(
            db.session.scalar(db.select(Notification.kind).where(Notification.recipient_id == self.reporter.id)),
            "report_published",
        )

    def test_opening_a_single_item_marks_only_that_item_read_and_routes_to_alert(self) -> None:
        queue_review_outcome_notifications(self.alert)
        second = Notification(
            recipient=self.recipient,
            kind="report_needs_moderation",
            title="Another update",
            body="This must remain unread.",
        )
        db.session.add(second)
        db.session.commit()
        first = db.session.scalar(
            db.select(Notification).where(Notification.recipient_id == self.recipient.id, Notification.kind == "alert_published")
        )
        self.sign_in_as(self.recipient)

        response = self.client.get(f"/notifications/{first.id}/open")
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/alerts/{self.alert.id}", response.headers["Location"])
        self.assertTrue(db.session.get(Notification, first.id).is_read)
        self.assertFalse(db.session.get(Notification, second.id).is_read)
        self.assertIn(b"notification-badge", self.client.get("/dashboard").data)

    def test_mark_all_and_closure_updates_are_persisted(self) -> None:
        queue_review_outcome_notifications(self.alert)
        db.session.commit()
        self.sign_in_as(self.recipient)
        response = self.client.post("/notifications/mark-seen", data={"filter": "unread"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/notifications?filter=unread", response.headers["Location"])
        self.assertTrue(
            all(
                db.session.scalars(
                    db.select(Notification.is_read).where(Notification.recipient_id == self.recipient.id)
                ).all()
            )
        )

        former_recipients = eligible_recipients(self.alert, [self.reporter, self.recipient, self.opted_out])
        self.alert.status = AlertStatus.REPORTED_FOUND
        queue_closure_notifications(self.alert, former_recipients, action="reported_found")
        db.session.commit()
        closure = db.session.scalar(
            db.select(Notification).where(Notification.recipient_id == self.recipient.id, Notification.kind == "reported_found")
        )
        self.assertIsNotNone(closure)
        self.assertFalse(closure.is_read)


if __name__ == "__main__":
    unittest.main()
