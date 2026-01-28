from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class User(AbstractUser):
    class Role(models.TextChoices):
        TEACHER = "TEACHER", "Teacher"
        STUDENT = "STUDENT", "Student"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    # Zambia-friendly: store phone (for OTP or payouts later)
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        validators=[
            RegexValidator(
                regex=r"^\+?\d{9,15}$",
                message="Phone number must be digits and can start with +. Example: +26097xxxxxxx",
            )
        ],
    )

    # Only verified teachers can earn
    is_teacher_verified = models.BooleanField(default=False)

    def is_teacher(self) -> bool:
        return self.role == self.Role.TEACHER

    def is_student(self) -> bool:
        return self.role == self.Role.STUDENT


class TeacherProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="teacher_profile")
    display_name = models.CharField(max_length=120)
    bio = models.TextField(blank=True)

    # payout details (Zambia focus)
    payout_mobile_money_number = models.CharField(max_length=20, blank=True)
    payout_network = models.CharField(max_length=30, blank=True)  # Airtel, MTN, Zamtel, etc.

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    verified_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.display_name} ({self.status})"
