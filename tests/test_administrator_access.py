"""T42 access-control and navigation coverage for the administration entry point."""

import unittest

from app import create_app
from app.extensions import db
from app.models import User, UserRole


class AdministratorAccessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.citizen = User(phone_number="+237692000051", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        self.moderator = User(phone_number="+237692000052", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.MODERATOR)
        self.admin = User(phone_number="+237692000053", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        db.session.add_all([self.citizen, self.moderator, self.admin])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def test_admin_entry_is_hidden_from_moderators_and_forbidden_to_non_admins(self) -> None:
        anonymous = self.client.get("/admin")
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn("/sign-in", anonymous.headers["Location"])

        self.sign_in_as(self.citizen)
        self.assertEqual(self.client.get("/admin").status_code, 403)

        self.sign_in_as(self.moderator)
        self.assertEqual(self.client.get("/admin").status_code, 403)
        moderator_dashboard = self.client.get("/dashboard")
        self.assertIn(b"Moderator", moderator_dashboard.data)
        self.assertNotIn(b"Administration</span>", moderator_dashboard.data)

    def test_administrator_receives_admin_navigation_and_private_entry_point(self) -> None:
        self.sign_in_as(self.admin)
        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Administration workspace", response.data)
        self.assertIn(b"Hospital verification", response.data)
        self.assertIn(b"Moderator queue", response.data)
        self.assertIn(b'href="/admin"', response.data)
        self.assertIn(b'href="/moderator"', response.data)


if __name__ == "__main__":
    unittest.main()
