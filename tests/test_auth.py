"""Tests for simulated phone OTP authentication and session access."""

import unittest

from app import create_app
from app.extensions import db
from app.models import User


class AuthenticationTestCase(unittest.TestCase):
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
        db.session.add(
            User(
                phone_number="+237612345678",
                display_name="Amina N.",
                country="Cameroon",
                primary_region="Centre",
                is_phone_verified=True,
            )
        )
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_protected_page_redirects_to_sign_in(self) -> None:
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/sign-in", response.headers["Location"])

    def test_demo_otp_creates_a_user_session(self) -> None:
        response = self.client.post("/sign-in", data={"phone_number": "+237 612 345 678"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/verify-otp", response.headers["Location"])
        response = self.client.post("/verify-otp", data={"otp_code": "123456"})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/dashboard"))
        self.assertEqual(self.client.get("/dashboard").status_code, 200)

    def test_invalid_otp_keeps_user_anonymous(self) -> None:
        self.client.post("/sign-in", data={"phone_number": "+237612345678"})
        response = self.client.post("/verify-otp", data={"otp_code": "000000"})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"not valid", response.data)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_sign_in_accepts_cemac_numbers_and_rejects_invalid_ones(self) -> None:
        for phone_number in (
            "+23512345678",
            "+23612345678",
            "+237512345678",
            "+240123456789",
            "+24174001122",
            "+242123456789",
        ):
            response = self.client.post("/sign-in", data={"phone_number": phone_number})
            self.assertEqual(response.status_code, 302)
            self.assertIn("/verify-otp", response.headers["Location"])

        for phone_number in ("+243123456789", "+23761234567"):
            response = self.client.post("/sign-in", data={"phone_number": phone_number})
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"valid CEMAC phone number", response.data)

        response = self.client.post("/sign-in", data={"phone_number": "+237 612 345 678"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("/verify-otp", response.headers["Location"])

    def test_opening_notifications_can_clear_the_unread_count(self) -> None:
        self.client.post("/sign-in", data={"phone_number": "+237612345678"})
        self.client.post("/verify-otp", data={"otp_code": "123456"})
        self.assertIn(b"notification-badge", self.client.get("/dashboard").data)
        response = self.client.post("/notifications/mark-seen")
        self.assertEqual(response.get_json(), {"unread_count": 0})
        self.assertNotIn(b"notification-badge", self.client.get("/dashboard").data)


if __name__ == "__main__":
    unittest.main()
