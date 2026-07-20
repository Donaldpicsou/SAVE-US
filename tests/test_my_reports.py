"""Tests for the private report-management workspace and closure audit trail."""

import unittest

from app import create_app
from app.extensions import db
from app.models import Alert, AlertStatus, AlertType, ReportAction, User


class MyReportsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(
            {"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"}
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.user = User(
            phone_number="+237644000000",
            display_name="Report owner",
            country="Cameroon",
            primary_region="Centre",
            is_phone_verified=True,
        )
        self.other_user = User(
            phone_number="+237644000001",
            display_name="Other reporter",
            country="Cameroon",
            primary_region="Littoral",
            is_phone_verified=True,
        )
        db.session.add_all([self.user, self.other_user])
        db.session.commit()
        self.client = self.app.test_client()
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = self.user.id

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def add_report(self, title, status, *, reporter=None, alert_type=AlertType.MISSING_PERSON):
        report = Alert(
            reporter=reporter or self.user,
            alert_type=alert_type,
            status=status,
            title=title,
            country="Cameroon",
            region="Centre",
            approximate_zone="Mfoundi district",
            public_summary=f"Public summary for {title}",
        )
        db.session.add(report)
        db.session.commit()
        return report

    def test_workspace_lists_only_owned_reports_and_supports_filters(self) -> None:
        draft = self.add_report("Draft for Awa", AlertStatus.DRAFT)
        published = self.add_report("Published for Beni", AlertStatus.PUBLISHED)
        self.add_report("Other reporter private case", AlertStatus.PUBLISHED, reporter=self.other_user)

        response = self.client.get("/reports")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Draft for Awa", response.data)
        self.assertIn(b"Published for Beni", response.data)
        self.assertNotIn(b"Other reporter private case", response.data)
        self.assertIn(f"/report/missing-person?draft={draft.id}".encode(), response.data)
        self.assertIn(f"/alerts/{published.id}".encode(), response.data)

        filtered = self.client.get("/reports?status=draft&q=awa")
        self.assertIn(b"Draft for Awa", filtered.data)
        self.assertNotIn(b"Published for Beni", filtered.data)

    def test_closing_a_report_requires_reason_and_creates_an_audit_action(self) -> None:
        report = self.add_report("Findable person", AlertStatus.PUBLISHED)

        missing_reason = self.client.post(
            f"/reports/{report.id}/close", data={"action": "reported_found", "reason": ""}
        )
        self.assertIn("action_error=", missing_reason.headers["Location"])
        self.assertEqual(db.session.get(Alert, report.id).status, AlertStatus.PUBLISHED)

        response = self.client.post(
            f"/reports/{report.id}/close",
            data={"action": "reported_found", "reason": "Located safely with family."},
        )
        self.assertTrue(response.headers["Location"].endswith("/reports"))
        closed_report = db.session.get(Alert, report.id)
        action = db.session.scalar(db.select(ReportAction).where(ReportAction.alert_id == report.id))
        self.assertEqual(closed_report.status, AlertStatus.REPORTED_FOUND)
        self.assertEqual((action.actor_id, action.action, action.reason), (self.user.id, "reported_found", "Located safely with family."))

    def test_reporter_can_open_own_published_alert_but_cannot_close_another_reporters_case(self) -> None:
        own_published = self.add_report("Owner public case", AlertStatus.PUBLISHED)
        other_report = self.add_report("Other private case", AlertStatus.PUBLISHED, reporter=self.other_user)

        self.assertEqual(self.client.get(f"/alerts/{own_published.id}").status_code, 200)
        self.assertEqual(
            self.client.post(
                f"/reports/{other_report.id}/close",
                data={"action": "withdrawn", "reason": "Not mine."},
            ).status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
