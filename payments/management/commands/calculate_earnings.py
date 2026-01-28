from decimal import Decimal, ROUND_HALF_UP

from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone

from payments.models import MonetizationSettings, EarningLedger
from views_tracker.models import QualifiedViewDailyAgg


class Command(BaseCommand):
    help = "Calculate daily teacher earnings from qualified views."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            help="Date to calculate in YYYY-MM-DD format (default: today)",
        )

    def handle(self, *args, **options):
        settings_obj = MonetizationSettings.get_solo()

        date_str = options.get("date")
        if date_str:
            target_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
        else:
            target_date = timezone.localdate()

        rate_per_1000 = Decimal(str(settings_obj.rate_per_1000_views))
        commission_percent = Decimal(str(settings_obj.platform_commission_percent))

        rows = (
            QualifiedViewDailyAgg.objects.filter(date=target_date)
            .values("teacher_id")
            .annotate(total_views=Sum("qualified_views_count"))
        )

        updated = 0

        for r in rows:
            teacher_id = r["teacher_id"]
            views = int(r["total_views"] or 0)
            if views <= 0:
                continue

            gross = (Decimal(views) / Decimal(1000)) * rate_per_1000

            commission = (gross * (commission_percent / Decimal(100))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            net = (gross - commission).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            gross = gross.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            EarningLedger.objects.update_or_create(
                teacher_id=teacher_id,
                date=target_date,
                defaults={
                    "qualified_views": views,
                    "gross_amount": gross,
                    "commission_amount": commission,
                    "net_amount": net,
                },
            )
            updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Calculated earnings for {target_date}. Teachers updated: {updated}"
        ))
