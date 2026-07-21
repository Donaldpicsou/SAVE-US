"""Tests for simulated phone OTP authentication and session access."""

import unittest

from app import create_app
from app.extensions import db
from app.models import Notification, User


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
        response = self.client.post("/sign-in", data={"phone_country_code": "237", "phone_number": "612 345 678"})
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

    def test_sign_in_accepts_national_numbers_after_country_selection_and_full_number_paste(self) -> None:
        for country_code, national_number in (
            ("235", "12 34 56 78"),
            ("236", "12 34 56 78"),
            ("237", "612 345 678"),
            ("240", "123 456 789"),
            ("241", "74 00 11 22"),
            ("242", "12 34 56 789"),
        ):
            response = self.client.post(
                "/sign-in", data={"phone_country_code": country_code, "phone_number": national_number}
            )
            self.assertEqual(response.status_code, 302)
            self.assertIn("/verify-otp", response.headers["Location"])

        response = self.client.post(
            "/sign-in", data={"phone_country_code": "237", "phone_number": "+241 74 00 11 22"}
        )
        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as browser_session:
            self.assertEqual(browser_session["pending_phone"], "+24174001122")

    def test_sign_in_page_explains_national_number_entry(self) -> None:
        page = self.client.get("/sign-in")
        self.assertIn(b'name="phone_country_code"', page.data)
        self.assertIn(b"national number without it", page.data)
        self.assertIn(b"(+237) ", page.data)
        self.assertNotIn(b"Cameroon (+237)", page.data)
        self.assertIn(b"New numbers create a SAVE-US account after verification.", page.data)
        self.assertNotIn(b"New to SAVE-US? Create an account", page.data)

    def test_opening_notifications_can_clear_the_unread_count(self) -> None:
        user = db.session.scalar(db.select(User).where(User.phone_number == "+237612345678"))
        db.session.add(
            Notification(
                recipient=user,
                kind="report_needs_moderation",
                title="Your report needs moderator review",
                body="Open the review to see the next steps.",
            )
        )
        db.session.commit()
        self.client.post("/sign-in", data={"phone_number": "+237612345678"})
        self.client.post("/verify-otp", data={"otp_code": "123456"})
        self.assertIn(b"notification-badge", self.client.get("/dashboard").data)
        response = self.client.post("/notifications/mark-seen")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/notifications?filter=all", response.headers["Location"])
        self.assertNotIn(b"notification-badge", self.client.get("/dashboard").data)

    def test_verified_user_can_update_display_name_with_server_validation(self) -> None:
        self.client.post("/sign-in", data={"phone_number": "+237612345678"})
        self.client.post("/verify-otp", data={"otp_code": "123456"})
        invalid = self.client.post("/account", data={"display_name": " "})
        self.assertEqual(invalid.status_code, 200)
        self.assertIn(b"display name between 2 and 120", invalid.data)

        saved = self.client.post("/account", data={"display_name": " Amina  Save-Us "})
        self.assertEqual(saved.status_code, 302)
        self.assertIn("/account?saved=1", saved.headers["Location"])
        user = db.session.scalar(db.select(User).where(User.phone_number == "+237612345678"))
        self.assertEqual(user.display_name, "Amina Save-Us")


if __name__ == "__main__":
    unittest.main()
