"""T46 restricted, searchable, privacy-minimised staff audit-log coverage."""

from datetime import datetime, timezone
import unittest

from app import create_app
from app.administration import record_administration_audit
from app.extensions import db
from app.models import Alert, AlertType, ReportAction, User, UserRole


class AdministrationAuditLogTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = User(phone_number="+237692000091", display_name="Audit Admin", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        self.moderator = User(phone_number="+237692000092", display_name="Review Moderator", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.MODERATOR)
        self.target = User(phone_number="+237692000093", display_name="Target Account", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        db.session.add_all([self.admin, self.moderator, self.target])
        db.session.flush()
        self.alert = Alert(reporter=self.target, alert_type=AlertType.MISSING_PERSON, title="Private family report title", country="Cameroon", region="Centre")
        db.session.add(self.alert)
        db.session.flush()
        record_administration_audit(
            actor_id=self.admin.id,
            action="moderator_granted",
            reason="Coverage review approved the temporary moderation role.",
            prior_value={"role": "citizen"},
            new_value={"role": "moderator"},
            target_user_id=self.target.id,
        )
        db.session.add(ReportAction(alert=self.alert, actor_id=self.moderator.id, action="moderator_publish", reason="Required fields and public summary were reviewed."))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def test_administrator_sees_combined_minimised_records_but_other_roles_cannot(self) -> None:
        self.sign_in_as(self.moderator)
        self.assertEqual(self.client.get("/admin/audit-log").status_code, 403)
        self.sign_in_as(self.admin)
        page = self.client.get("/admin/audit-log")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Moderator Granted", page.data)
        self.assertIn(b"Moderator Publish", page.data)
        self.assertIn(b"Administration", page.data)
        self.assertIn(b"Moderation", page.data)
        self.assertIn(f"Account #{self.target.id}".encode(), page.data)
        self.assertNotIn(self.target.phone_number.encode(), page.data)
        self.assertNotIn(b"Private family report title", page.data)

    def test_filters_by_author_action_report_or_account_and_date(self) -> None:
        self.sign_in_as(self.admin)
        by_author = self.client.get(f"/admin/audit-log?actor={self.moderator.id}")
        self.assertIn(b"Moderator Publish", by_author.data)
        self.assertEqual(by_author.data.count(b'<article class="audit-record">'), 1)
        by_action = self.client.get("/admin/audit-log?action=moderator_granted")
        self.assertIn(b"Moderator Granted", by_action.data)
        self.assertEqual(by_action.data.count(b'<article class="audit-record">'), 1)
        by_account = self.client.get("/admin/audit-log?subject=Target%20Account")
        self.assertIn(b"Moderator Granted", by_account.data)
        by_report = self.client.get(f"/admin/audit-log?subject={self.alert.id[:8]}")
        self.assertIn(b"Moderator Publish", by_report.data)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        by_date = self.client.get(f"/admin/audit-log?from={today}&to={today}")
        self.assertIn(b"Moderator Granted", by_date.data)
        self.assertIn(b"Moderator Publish", by_date.data)


if __name__ == "__main__":
    unittest.main()
