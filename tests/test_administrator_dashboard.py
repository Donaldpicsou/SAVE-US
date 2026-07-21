"""T47 safe aggregate operational dashboard coverage."""

from datetime import datetime, timedelta, timezone
import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertStatus, AlertType, HospitalVerificationRequest, HospitalVerificationStatus, ReportAction, User, UserRole


class AdministratorDashboardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = User(phone_number="+237692000101", display_name="Operations Admin", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        self.moderator = User(phone_number="+237692000102", display_name="Active Moderator", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.MODERATOR)
        self.reporter = User(phone_number="+237692000103", display_name="Private Reporter", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        db.session.add_all([self.admin, self.moderator, self.reporter])
        db.session.flush()
        now = datetime.now(timezone.utc)
        self.published = Alert(reporter=self.reporter, alert_type=AlertType.MISSING_PERSON, title="Private published report", country="Cameroon", region="Centre", status=AlertStatus.PUBLISHED, created_at=now - timedelta(hours=8))
        self.pending = Alert(reporter=self.reporter, alert_type=AlertType.SUSPECTED_ABDUCTION, title="Private pending report", country="Cameroon", region="Centre", status=AlertStatus.NEEDS_MODERATION, created_at=now - timedelta(hours=4))
        self.expired = Alert(reporter=self.reporter, alert_type=AlertType.ROAD_ACCIDENT, title="Private expired report", country="Cameroon", region="Centre", status=AlertStatus.EXPIRED, created_at=now - timedelta(days=2))
        db.session.add_all([self.published, self.pending, self.expired])
        db.session.flush()
        db.session.add(ReportAction(alert=self.published, actor_id=self.moderator.id, action="moderator_publish", reason="Safe operational decision.", created_at=now - timedelta(hours=2)))
        db.session.add(HospitalVerificationRequest(submitted_by_id=self.reporter.id, hospital_name="Private Hospital", country="Cameroon", region="Centre", contact_name="Private Contact", contact_phone="+237692000103", supporting_document_reference="private/evidence.pdf", status=HospitalVerificationStatus.PENDING))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def test_dashboard_shows_aggregate_operations_without_private_report_or_hospital_data(self) -> None:
        self.sign_in_as(self.admin)
        page = self.client.get("/admin")
        self.assertEqual(page.status_code, 200)
        for label in (b"Active alerts", b"Pending alerts", b"Expired alerts", b"Reports", b"Moderation workload", b"Hospital verification", b"Moderator activity"):
            self.assertIn(label, page.data)
        self.assertIn(b"Active Moderator", page.data)
        self.assertIn(b"private request awaiting review", page.data)
        self.assertNotIn(b"Private published report", page.data)
        self.assertNotIn(b"Private pending report", page.data)
        self.assertNotIn(b"Private Hospital", page.data)
        self.assertNotIn(self.reporter.phone_number.encode(), page.data)

    def test_dashboard_remains_administrator_only(self) -> None:
        self.sign_in_as(self.moderator)
        self.assertEqual(self.client.get("/admin").status_code, 403)


if __name__ == "__main__":
    unittest.main()
