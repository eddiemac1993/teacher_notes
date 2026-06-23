from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


MAX_PDF_SIZE = 5 * 1024 * 1024  # 5MB


def validate_pdf(value):
    if not value:
        return

    name = (getattr(value, "name", "") or "").lower()
    if not name.endswith(".pdf"):
        raise ValidationError("Only PDF files are allowed for attachments.")

    size = getattr(value, "size", 0) or 0
    if size > MAX_PDF_SIZE:
        raise ValidationError("PDF file too large. Max 5 MB.")


class BulletinPost(models.Model):
    class PostType(models.TextChoices):
        EVENT = "EVENT", "Event"
        JOB = "JOB", "Job"
        NOTICE = "NOTICE", "Notice"
        TENDER = "TENDER", "Tender / Procurement"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        AWARDED = "AWARDED", "Awarded"
        DRAFT = "DRAFT", "Draft"

    # Who posted it (school staff/admin)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bulletin_posts",
        help_text="User who created this bulletin post.",
    )

    post_type = models.CharField(
        max_length=20,
        choices=PostType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    title = models.CharField(max_length=180)
    summary = models.TextField(blank=True)
    body = models.TextField(blank=True)

    # Generic metadata
    organization_name = models.CharField(
        max_length=120,
        blank=True,
        help_text="e.g. 'Pemba High School'",
    )
    location = models.CharField(
        max_length=120,
        blank=True,
        help_text="e.g. 'Lusaka'",
    )
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)

    # Dates
    publish_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # Tender-specific fields (optional unless post_type = TENDER)
    reference_no = models.CharField(
        max_length=80,
        blank=True,
        help_text="e.g. 'KSS/PROC/01/2026'",
    )
    submission_deadline = models.DateTimeField(null=True, blank=True)
    attachment_pdf = models.FileField(
        upload_to="bulletins/",
        null=True,
        blank=True,
        validators=[validate_pdf],
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-publish_at", "-created_at"]
        indexes = [
            models.Index(fields=["post_type", "status"]),
            models.Index(fields=["-publish_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.post_type}: {self.title}"

    # -----------------------------
    # Validation
    # -----------------------------
    def clean(self):
        super().clean()

        # publish_at should not be after expires_at
        if self.expires_at and self.publish_at and self.expires_at <= self.publish_at:
            raise ValidationError({"expires_at": "Expiry must be after publish date/time."})

        # Tender validation rules
        if self.post_type == self.PostType.TENDER:
            errors = {}

            if not (self.reference_no or "").strip():
                errors["reference_no"] = "Reference number is required for tenders."

            if not self.submission_deadline:
                errors["submission_deadline"] = "Submission deadline is required for tenders."
            else:
                # deadline should be after publish_at (or now for safety)
                base_time = self.publish_at or timezone.now()
                if self.submission_deadline <= base_time:
                    errors["submission_deadline"] = "Deadline must be after publish date/time."

            if not self.attachment_pdf:
                errors["attachment_pdf"] = "Attach the tender document PDF (max 5MB)."

            if errors:
                raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # Ensure full_clean runs when saving from code (admin already calls it)
        self.full_clean()
        return super().save(*args, **kwargs)

    # -----------------------------
    # Convenience helpers
    # -----------------------------
    @property
    def is_tender(self) -> bool:
        return self.post_type == self.PostType.TENDER

    @property
    def is_expired(self) -> bool:
        return bool(self.expires_at and timezone.now() > self.expires_at)

    @property
    def is_published(self) -> bool:
        return self.publish_at <= timezone.now() and self.status != self.Status.DRAFT and not self.is_expired

    @property
    def author_display_name(self) -> str:
        """
        Safe name for templates:
        - Uses get_full_name() if first/last exists
        - Falls back to username
        - Falls back to 'System' if author is null
        """
        if not self.author:
            return "System"
        full = (self.author.get_full_name() or "").strip()
        return full if full else (getattr(self.author, "username", "") or "User")
