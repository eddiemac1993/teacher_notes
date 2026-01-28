from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
import os
import uuid


def validate_pdf_file(value):
    # size check (5MB)
    max_size = 5 * 1024 * 1024
    if value.size > max_size:
        raise ValidationError("PDF file too large. Maximum allowed size is 5 MB.")

    # extension check
    name = (value.name or "").lower()
    if not name.endswith(".pdf"):
        raise ValidationError("Only PDF files are allowed.")


def pdf_upload_path(instance, filename):
    """
    Store PDFs with a short, safe filename:
    pdfs/<uuid>.pdf
    """
    ext = os.path.splitext(filename)[1].lower()
    return f"pdfs/{uuid.uuid4().hex}{ext}"


class Subject(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class GradeLevel(models.Model):
    name = models.CharField(max_length=80, unique=True)

    def __str__(self):
        return self.name


class DocumentPost(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="document_posts",
    )

    title = models.CharField(max_length=200)
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT)
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.PROTECT)
    topic = models.CharField(max_length=200)

    pdf_file = models.FileField(
        upload_to=pdf_upload_path,
        validators=[validate_pdf_file],
    )

    external_video_url = models.URLField(blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"
