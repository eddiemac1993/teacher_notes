from decimal import Decimal
from django.contrib import admin
from django.utils import timezone

from .models import MonetizationSettings, EarningLedger, PayoutRequest, PayoutTransaction


@admin.register(MonetizationSettings)
class MonetizationSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        # enforce single row
        return not MonetizationSettings.objects.exists()


@admin.register(EarningLedger)
class EarningLedgerAdmin(admin.ModelAdmin):
    list_display = ("teacher", "date", "qualified_views", "gross_amount", "commission_amount", "net_amount")
    list_filter = ("date",)
    search_fields = ("teacher__username", "teacher__email")


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = ("teacher", "amount", "status", "requested_at", "processed_at")
    list_filter = ("status",)
    search_fields = ("teacher__username", "teacher__email")
    actions = ["approve_requests", "reject_requests", "mark_paid"]

    @admin.action(description="Approve selected payout requests")
    def approve_requests(self, request, queryset):
        now = timezone.now()
        queryset.update(status=PayoutRequest.Status.APPROVED, processed_at=now)

    @admin.action(description="Reject selected payout requests")
    def reject_requests(self, request, queryset):
        now = timezone.now()
        queryset.update(status=PayoutRequest.Status.REJECTED, processed_at=now)

    @admin.action(description="Mark selected payout requests as PAID (creates transactions if missing)")
    def mark_paid(self, request, queryset):
        now = timezone.now()
        for pr in queryset:
            pr.status = PayoutRequest.Status.PAID
            pr.processed_at = now
            pr.save(update_fields=["status", "processed_at"])
            PayoutTransaction.objects.get_or_create(
                payout_request=pr,
                defaults={"paid_at": now, "reference_number": "", "method_details_snapshot": {}},
            )


@admin.register(PayoutTransaction)
class PayoutTransactionAdmin(admin.ModelAdmin):
    list_display = ("payout_request", "reference_number", "paid_at")
    search_fields = ("reference_number", "payout_request__teacher__username")
