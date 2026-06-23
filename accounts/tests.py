from django.test import TestCase

# Create your tests here.
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase

from .admin import TeacherProfileAdmin
from .models import TeacherProfile, User


class TeacherApprovalAdminTests(TestCase):
    def test_profile_admin_save_syncs_user_verification(self):
        user = User.objects.create_user(username="teacher", password="pass", role=User.Role.TEACHER)
        profile = TeacherProfile.objects.create(user=user, display_name="Teacher One")

        profile.status = TeacherProfile.Status.VERIFIED
        request = RequestFactory().post("/")
        admin = TeacherProfileAdmin(TeacherProfile, AdminSite())
        admin.save_model(request, profile, form=None, change=True)

        user.refresh_from_db()
        profile.refresh_from_db()
        self.assertTrue(user.is_teacher_verified)
        self.assertIsNotNone(profile.verified_at)
