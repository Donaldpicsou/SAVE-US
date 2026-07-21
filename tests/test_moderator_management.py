"""T44 administrator-only moderator management and safeguard coverage."""

import unittest

from app import create_app
from app.extensions import db
from app.models import AdministrationAuditEntry, User, UserRole


class ModeratorManagementTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-secret", "SQLALCHEMY_DATABASE_URI": "sqlite://"})
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.admin = User(phone_number="+237692000071", display_name="Amina Admin", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        self.other_admin = User(phone_number="+237692000072", display_name="Second Admin", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.ADMINISTRATOR)
        self.hospital_user = User(phone_number="+237692000073", display_name="Dr. Ndom", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.HOSPITAL_REPRESENTATIVE)
        self.seeded_moderator = User(phone_number="+237692000074", display_name="Existing Moderator", country="Cameroon", primary_region="Centre", is_phone_verified=True, role=UserRole.MODERATOR)
        self.citizen = User(phone_number="+237692000075", display_name="Citizen User", country="Cameroon", primary_region="Centre", is_phone_verified=True)
        db.session.add_all([self.admin, self.other_admin, self.hospital_user, self.seeded_moderator, self.citizen])
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def sign_in_as(self, user: User) -> None:
        with self.client.session_transaction() as browser_session:
            browser_session["user_id"] = user.id

    def post_change(self, user: User, action: str, reason: str = "Operational coverage needs this reviewed access."):
        self.sign_in_as(self.admin)
        return self.client.post(
            f"/admin/moderators/{user.id}/role",
            data={"action": action, "reason": reason, "q": user.display_name or ""},
        )

    def test_administrator_can_search_and_only_administrators_can_access_management(self) -> None:
        self.sign_in_as(self.citizen)
        self.assertEqual(self.client.get("/admin/moderators").status_code, 403)
        self.sign_in_as(self.admin)
        response = self.client.get("/admin/moderators?q=Ndom")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Dr. Ndom", response.data)
        self.assertNotIn(b"Citizen User", response.data)

    def test_grant_then_revoke_restores_recorded_prior_role_and_audits_both_actions(self) -> None:
        self.assertEqual(self.post_change(self.hospital_user, "grant").status_code, 302)
        self.assertEqual(db.session.get(User, self.hospital_user.id).role, UserRole.MODERATOR)
        granted = db.session.scalar(db.select(AdministrationAuditEntry).where(AdministrationAuditEntry.action == "moderator_granted"))
        self.assertEqual(granted.prior_value, {"role": "hospital_representative"})
        self.assertEqual(granted.new_value, {"role": "moderator"})
        self.assertEqual(granted.target_user_id, self.hospital_user.id)

        self.assertEqual(self.post_change(self.hospital_user, "revoke", "Rotation completed; restore hospital duties.").status_code, 302)
        self.assertEqual(db.session.get(User, self.hospital_user.id).role, UserRole.HOSPITAL_REPRESENTATIVE)
        revoked = db.session.scalar(db.select(AdministrationAuditEntry).where(AdministrationAuditEntry.action == "moderator_revoked"))
        self.assertEqual(revoked.prior_value, {"role": "moderator"})
        self.assertEqual(revoked.new_value, {"role": "hospital_representative"})

    def test_seeded_moderator_without_prior_grant_returns_to_citizen(self) -> None:
        self.assertEqual(self.post_change(self.seeded_moderator, "revoke").status_code, 302)
        self.assertEqual(db.session.get(User, self.seeded_moderator.id).role, UserRole.CITIZEN)

    def test_reason_self_change_and_administrator_protections_prevent_unsafe_changes(self) -> None:
        missing_reason = self.post_change(self.citizen, "grant", "")
        self.assertIn(b"reason is required", self.client.get(missing_reason.headers["Location"]).data)
        self.assertEqual(db.session.get(User, self.citizen.id).role, UserRole.CITIZEN)

        self_change = self.post_change(self.admin, "revoke")
        self.assertIn(b"own administrator role", self.client.get(self_change.headers["Location"]).data)
        self.assertEqual(db.session.get(User, self.admin.id).role, UserRole.ADMINISTRATOR)

        administrator_attempt = self.post_change(self.other_admin, "revoke")
        self.assertIn(b"Administrator roles cannot be changed", self.client.get(administrator_attempt.headers["Location"]).data)
        self.assertEqual(db.session.get(User, self.other_admin.id).role, UserRole.ADMINISTRATOR)

        db.session.delete(self.other_admin)
        db.session.commit()
        last_admin_attempt = self.post_change(self.admin, "revoke")
        self.assertIn(b"last administrator", self.client.get(last_admin_attempt.headers["Location"]).data.lower())
        self.assertEqual(db.session.get(User, self.admin.id).role, UserRole.ADMINISTRATOR)


if __name__ == "__main__":
    unittest.main()
