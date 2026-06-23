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
        DRAFT = "DRAFT", "Draft"
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
    description = models.TextField(blank=True)
    exam_year = models.PositiveIntegerField(blank=True, null=True)
    language = models.CharField(max_length=40, default="English")
    has_answers = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

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


class StudentBookmark(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookmarks")
    post = models.ForeignKey(DocumentPost, on_delete=models.CASCADE, related_name="bookmarked_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "post")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.student_id} saved {self.post_id}"


class StudentMaterialActivity(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="material_activity")
    post = models.ForeignKey(DocumentPost, on_delete=models.CASCADE, related_name="student_activity")
    first_viewed_at = models.DateTimeField(auto_now_add=True)
    last_viewed_at = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=1)
    downloaded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ("student", "post")
        ordering = ["-last_viewed_at"]

    def __str__(self):
        return f"{self.student_id} activity {self.post_id}"


class MaterialReview(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="material_reviews")
    post = models.ForeignKey(DocumentPost, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "post")
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.post_id} rating={self.rating}"


class MaterialReport(models.Model):
    class Reason(models.TextChoices):
        WRONG_CONTENT = "WRONG_CONTENT", "Wrong or inaccurate content"
        LOW_QUALITY = "LOW_QUALITY", "Low quality"
        DUPLICATE = "DUPLICATE", "Duplicate material"
        INAPPROPRIATE = "INAPPROPRIATE", "Inappropriate content"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        REVIEWING = "REVIEWING", "Reviewing"
        RESOLVED = "RESOLVED", "Resolved"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="material_reports")
    post = models.ForeignKey(DocumentPost, on_delete=models.CASCADE, related_name="reports")
    reason = models.CharField(max_length=30, choices=Reason.choices)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report {self.post_id} {self.reason}"
