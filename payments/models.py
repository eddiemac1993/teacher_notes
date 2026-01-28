from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class MonetizationSettings(models.Model):
    """
    Single-row settings table controlled by admin.
    """
    rate_per_1000_views = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("50.00"))
    platform_commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("30.00"))
    minimum_payout = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("200.00"))
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Monetization Settings"

    @classmethod
    def get_solo(cls):
        obj, _created = cls.objects.get_or_create(id=1)
        return obj


class EarningLedger(models.Model):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()

    qualified_views = models.PositiveIntegerField(default=0)

    gross_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    net_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("teacher", "date")
        indexes = [models.Index(fields=["teacher", "date"])]

    def __str__(self):
        return f"{self.teacher_id} {self.date} net={self.net_amount}"


class PayoutRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PAID = "PAID", "Paid"

    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(blank=True, null=True)
    admin_note = models.TextField(blank=True)

    def __str__(self):
        return f"{self.teacher_id} {self.amount} {self.status}"


class PayoutTransaction(models.Model):
    payout_request = models.OneToOneField(PayoutRequest, on_delete=models.CASCADE, related_name="transaction")

    reference_number = models.CharField(max_length=120, blank=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    # snapshot payout details at time of paying (optional)
    method_details_snapshot = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Txn payout={self.payout_request_id}"
