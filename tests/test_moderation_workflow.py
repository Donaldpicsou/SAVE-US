"""Tests for the restricted, auditable human moderation workflow (T40)."""

import tempfile
import unittest

from app import create_app
from app.extensions import db
from app.models import (
    AIReview,
    Alert,
    AlertPreference,
    AlertStatus,
    AlertType,
    Notification,
    ReportAction,
    RoadAccidentDetails,
    RoadAccidentMediaReview,
    SuspectedAbductionDetails,
    User,
    UserRole,
)


class ModerationWorkflowTestCase(unittest.TestCase):
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
        self.reporter = User(phone_number="+237691000001", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        self.moderator = User(phone_number="+237691000002", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.MODERATOR)
        self.citizen = User(phone_number="+237691000003", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        self.subscriber = User(phone_number="+237691000004", country="Cameroon", primary_region="Littoral", is_phone_verified=True)
        db.session.add_all([
            self.reporter,
            self.moderator,
            self.citizen,
            self.subscriber,
            AlertPreference(user=self.subscriber, enabled_categories=["suspected_abduction"]),
        ])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.upload_directory.cleanup()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def abduction_for_review(self) -> Alert:
        alert = Alert(
            reporter=self.reporter,
            alert_type=AlertType.SUSPECTED_ABDUCTION,
            status=AlertStatus.NEEDS_MODERATION,
            title="Possible abduction near Mfoundi",
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi district",
        )
        db.session.add_all([
            alert,
            SuspectedAbductionDetails(
                alert=alert,
                description="Witnesses described a vehicle leaving the market.",
                circumstances="The family could not contact the person afterwards.",
                private_contact="+237 691 000 001",
            ),
            AIReview(
                alert=alert,
                public_summary="A suspected abduction was reported near Mfoundi district.",
                extracted_data={},
                missing_fields=[],
                duplicate_candidates=[],
                confidence_score=76,
                fraud_risk_score=15,
                decision="needs_moderation",
                reasons=["A moderator must verify the available information."],
                source="test",
            ),
        ])
        db.session.commit()
        return alert

    def test_only_moderators_can_review_and_publish_with_an_audit_record(self) -> None:
        alert = self.abduction_for_review()
        self.sign_in_as(self.citizen)
        self.assertEqual(self.client.get(f"/moderator/alerts/{alert.id}").status_code, 403)

        self.sign_in_as(self.moderator)
        review = self.client.get(f"/moderator/alerts/{alert.id}")
        self.assertEqual(review.status_code, 200)
        self.assertIn(b"Private contact", review.data)
        self.assertIn(b"Record moderation decision", review.data)
        response = self.client.post(
            f"/moderator/alerts/{alert.id}/decision",
            data={"decision": "publish", "reason": "Independent witness details and AI review were checked."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(db.session.get(Alert, alert.id).status, AlertStatus.PUBLISHED)
        action = db.session.scalar(db.select(ReportAction).where(ReportAction.alert_id == alert.id))
        self.assertEqual((action.actor_id, action.action), (self.moderator.id, "moderator_publish"))
        self.assertEqual(
            db.session.scalar(db.select(Notification.kind).where(Notification.recipient_id == self.subscriber.id, Notification.alert_id == alert.id)),
            "alert_published",
        )

    def test_moderator_can_reject_or_withdraw_but_cannot_publish_blocked_road_media(self) -> None:
        alert = self.abduction_for_review()
        self.sign_in_as(self.moderator)
        self.client.post(
            f"/moderator/alerts/{alert.id}/decision",
            data={"decision": "reject", "reason": "The supporting information could not be verified."},
        )
        self.assertEqual(db.session.get(Alert, alert.id).status, AlertStatus.REJECTED)
        self.assertEqual(
            db.session.scalar(db.select(Notification.kind).where(Notification.recipient_id == self.reporter.id, Notification.alert_id == alert.id)),
            "moderation_update",
        )

        road_alert = Alert(
            reporter=self.reporter,
            alert_type=AlertType.ROAD_ACCIDENT,
            status=AlertStatus.NEEDS_MODERATION,
            title="Blocked road evidence",
            country="Cameroon",
            region="Centre",
            approximate_zone="N1",
        )
        db.session.add_all([
            road_alert,
            RoadAccidentDetails(
                alert=road_alert,
                occurred_at=None,
                manual_location="N1",
                victim_count=1,
                immediate_needs="Traffic support",
                description="A collision was reported.",
                media_references=["road_accident/blocked/image.png"],
            ),
            RoadAccidentMediaReview(
                alert=road_alert,
                media_reference="road_accident/blocked/image.png",
                status="blocked",
                reason="The image is unsafe for community sharing.",
                source="test",
            ),
        ])
        db.session.commit()
        blocked = self.client.post(
            f"/moderator/alerts/{road_alert.id}/decision",
            data={"decision": "publish", "reason": "This must not override a blocked image."},
        )
        self.assertEqual(blocked.status_code, 302)
        self.assertEqual(db.session.get(Alert, road_alert.id).status, AlertStatus.NEEDS_MODERATION)

    def test_moderator_can_withdraw_a_published_abduction_with_a_reasoned_audit_record(self) -> None:
        alert = self.abduction_for_review()
        alert.status = AlertStatus.PUBLISHED
        alert.public_summary = alert.ai_review.public_summary
        db.session.commit()
        self.sign_in_as(self.moderator)

        response = self.client.post(
            f"/moderator/alerts/{alert.id}/decision",
            data={"decision": "withdraw", "reason": "A post-publication safety concern requires immediate removal."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(db.session.get(Alert, alert.id).status, AlertStatus.WITHDRAWN)
        audit = db.session.scalar(
            db.select(ReportAction).where(
                ReportAction.alert_id == alert.id,
                ReportAction.action == "moderator_withdraw",
            )
        )
        self.assertEqual(audit.actor_id, self.moderator.id)
        self.assertEqual(
            db.session.scalar(
                db.select(Notification.kind).where(
                    Notification.recipient_id == self.subscriber.id,
                    Notification.alert_id == alert.id,
                    Notification.kind == "withdrawn",
                )
            ),
            "withdrawn",
        )


if __name__ == "__main__":
    unittest.main()
