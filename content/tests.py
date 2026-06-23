from django.test import TestCase

# Create your tests here.
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from views_tracker.models import QualifiedViewDailyAgg
from .models import DocumentPost, GradeLevel, MaterialReport, MaterialReview, StudentBookmark, Subject


class ContentFlowTests(TestCase):
    def setUp(self):
        self.subject = Subject.objects.create(name="Mathematics")
        self.grade = GradeLevel.objects.create(name="Grade 9")
        self.teacher = User.objects.create_user(
            username="teacher",
            password="pass12345",
            role=User.Role.TEACHER,
            is_teacher_verified=True,
        )
        self.post = DocumentPost.objects.create(
            teacher=self.teacher,
            title="Algebra Revision",
            subject=self.subject,
            grade_level=self.grade,
            topic="Linear equations",
            pdf_file=SimpleUploadedFile("algebra.pdf", b"%PDF-1.4\n%", content_type="application/pdf"),
            status=DocumentPost.Status.APPROVED,
        )

    def test_browse_searches_subject_and_topic(self):
        response = self.client.get(reverse("content:browse"), {"q": "linear"})
        self.assertContains(response, "Algebra Revision")

        response = self.client.get(reverse("content:browse"), {"q": "mathematics"})
        self.assertContains(response, "Algebra Revision")

    def test_post_detail_does_not_create_qualified_view(self):
        student = User.objects.create_user(username="student", password="pass12345", role=User.Role.STUDENT)
        self.client.force_login(student)

        response = self.client.get(reverse("content:post_detail", args=[self.post.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(QualifiedViewDailyAgg.objects.count(), 0)

    def test_unverified_teacher_cannot_upload(self):
        self.teacher.is_teacher_verified = False
        self.teacher.save(update_fields=["is_teacher_verified"])
        self.client.force_login(self.teacher)

        response = self.client.get(reverse("content:upload_post"))

        self.assertRedirects(response, reverse("content:teacher_dashboard"))

    def test_student_can_bookmark_review_and_report(self):
        student = User.objects.create_user(username="student2", password="pass12345", role=User.Role.STUDENT)
        self.client.force_login(student)

        self.client.post(reverse("content:toggle_bookmark", args=[self.post.id]))
        self.client.post(reverse("content:submit_review", args=[self.post.id]), {"rating": 5, "comment": "Helpful"})
        self.client.post(reverse("content:report_material", args=[self.post.id]), {"reason": "LOW_QUALITY", "note": "Needs checking"})

        self.assertTrue(StudentBookmark.objects.filter(student=student, post=self.post).exists())
        self.assertTrue(MaterialReview.objects.filter(student=student, post=self.post, rating=5).exists())
        self.assertTrue(MaterialReport.objects.filter(student=student, post=self.post).exists())

    def test_staff_admin_queue_loads(self):
        admin = User.objects.create_user(username="admin", password="pass12345", is_staff=True)
        self.client.force_login(admin)

        response = self.client.get(reverse("content:admin_queue"))

        self.assertEqual(response.status_code, 200)
