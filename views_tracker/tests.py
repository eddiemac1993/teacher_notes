from django.test import TestCase

# Create your tests here.
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from content.models import DocumentPost, GradeLevel, Subject
from .models import DocumentOpenSession, QualifiedViewDailyAgg


class ReaderTrackingTests(TestCase):
    def setUp(self):
        subject = Subject.objects.create(name="Science")
        grade = GradeLevel.objects.create(name="Grade 8")
        self.teacher = User.objects.create_user(
            username="teacher",
            password="pass12345",
            role=User.Role.TEACHER,
            is_teacher_verified=True,
        )
        self.student = User.objects.create_user(username="student", password="pass12345", role=User.Role.STUDENT)
        self.post = DocumentPost.objects.create(
            teacher=self.teacher,
            title="Forces",
            subject=subject,
            grade_level=grade,
            topic="Motion and forces",
            pdf_file=SimpleUploadedFile("forces.pdf", b"%PDF-1.4\n%", content_type="application/pdf"),
            status=DocumentPost.Status.APPROVED,
        )

    def test_reader_must_interact_and_reach_threshold_to_qualify(self):
        self.client.force_login(self.student)

        response = self.client.post(reverse("views_tracker:start"), {"post_id": self.post.id})
        self.assertTrue(response.json()["ok"])
        self.assertFalse(response.json()["qualified"])
        self.assertEqual(QualifiedViewDailyAgg.objects.count(), 0)

        session = DocumentOpenSession.objects.get(id=response.json()["session_id"])
        self.client.post(reverse("views_tracker:interact"), {"session_id": session.id})
        session.seconds_accumulated = 20
        session.last_heartbeat_at = timezone.now() - timezone.timedelta(seconds=30)
        session.save(update_fields=["seconds_accumulated", "last_heartbeat_at"])

        response = self.client.post(reverse("views_tracker:heartbeat"), {"session_id": session.id})

        self.assertTrue(response.json()["qualified"])
        self.assertEqual(QualifiedViewDailyAgg.objects.count(), 1)
