from decimal import Decimal
from django.db.models import Sum

from .models import EarningLedger, PayoutRequest, MonetizationSettings


def get_available_balance(teacher) -> Decimal:
    earned = (
        EarningLedger.objects.filter(teacher=teacher)
        .aggregate(s=Sum("net_amount"))
        .get("s") or Decimal("0.00")
    )

    # money reserved/paid out: all APPROVED and PAID count as deducted
    deducted = (
        PayoutRequest.objects.filter(teacher=teacher, status__in=["APPROVED", "PAID"])
        .aggregate(s=Sum("amount"))
        .get("s") or Decimal("0.00")
    )

    pending = (
        PayoutRequest.objects.filter(teacher=teacher, status="PENDING")
        .aggregate(s=Sum("amount"))
        .get("s") or Decimal("0.00")
    )

    # Don’t allow requesting against pending requests
    return earned - deducted - pending
