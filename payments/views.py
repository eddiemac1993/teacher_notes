from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import redirect, render

from .forms import PayoutRequestForm
from .models import PayoutRequest, MonetizationSettings, EarningLedger
from .services import get_available_balance


@login_required
def teacher_payouts(request):
    if getattr(request.user, "role", None) != "TEACHER":
        raise Http404

    settings_obj = MonetizationSettings.get_solo()
    balance = get_available_balance(request.user)

    can_request = bool(request.user.is_teacher_verified) and balance >= settings_obj.minimum_payout

    # ✅ Lifetime totals (views + earnings) from EarningLedger
    ledger_totals = EarningLedger.objects.filter(teacher=request.user).aggregate(
        total_views=Sum("qualified_views"),
        total_gross=Sum("gross_amount"),
        total_commission=Sum("commission_amount"),
        total_net=Sum("net_amount"),
    )
    total_views = ledger_totals["total_views"] or 0
    total_gross = ledger_totals["total_gross"] or Decimal("0.00")
    total_commission = ledger_totals["total_commission"] or Decimal("0.00")
    total_net = ledger_totals["total_net"] or Decimal("0.00")

    if request.method == "POST":
        if not request.user.is_teacher_verified:
            messages.error(request, "You must be verified before requesting payouts.")
            return redirect("payments:teacher_payouts")

        form = PayoutRequestForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data["amount"]

            # must be above minimum threshold and within balance
            if amount < settings_obj.minimum_payout:
                form.add_error("amount", f"Minimum payout is ZMW {settings_obj.minimum_payout}.")
            elif amount > balance:
                form.add_error("amount", f"Insufficient balance. Available: ZMW {balance}.")
            else:
                pr = form.save(commit=False)
                pr.teacher = request.user
                pr.status = PayoutRequest.Status.PENDING
                pr.save()
                messages.success(request, "Payout request submitted and pending admin approval.")
                return redirect("payments:teacher_payouts")
    else:
        form = PayoutRequestForm()

    payout_history = PayoutRequest.objects.filter(teacher=request.user).order_by("-requested_at")[:50]

    # Optional: show last 30 days earnings
    recent_earnings = EarningLedger.objects.filter(teacher=request.user).order_by("-date")[:30]

    return render(
        request,
        "payments/teacher_payouts.html",
        {
            "settings_obj": settings_obj,
            "balance": balance,
            "can_request": can_request,
            "form": form,
            "payout_history": payout_history,
            "recent_earnings": recent_earnings,

            # ✅ Add these to show "views gained" + "earned amount" on payouts page
            "total_views": total_views,
            "total_gross": total_gross,
            "total_commission": total_commission,
            "total_net": total_net,
        },
    )
