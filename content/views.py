# content/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from views_tracker.models import PostDetailUniqueView, QualifiedViewDailyAgg
from .forms import DocumentPostForm
from .models import DocumentPost, Subject, GradeLevel


def home(request):
    posts = list(
        DocumentPost.objects.filter(status=DocumentPost.Status.APPROVED)
        .select_related("teacher", "subject", "grade_level")[:20]
    )

    # Build a per-post view map from aggregation table
    post_ids = [p.id for p in posts]
    totals = (
        QualifiedViewDailyAgg.objects.filter(post_id__in=post_ids)
        .values("post_id")
        .annotate(total=Sum("qualified_views_count"))
    )
    totals_map = {row["post_id"]: (row["total"] or 0) for row in totals}

    # Attach views onto each post object
    for p in posts:
        p.views_total = totals_map.get(p.id, 0)

    return render(request, "content/home.html", {"posts": posts})

def browse(request):
    q = (request.GET.get("q") or "").strip()
    subject_id = request.GET.get("subject") or ""
    grade_id = request.GET.get("grade") or ""

    posts = (
        DocumentPost.objects.filter(status=DocumentPost.Status.APPROVED)
        .select_related("teacher", "subject", "grade_level")
    )

    if q:
        posts = posts.filter(title__icontains=q) | posts.filter(topic__icontains=q)

    if subject_id.isdigit():
        posts = posts.filter(subject_id=int(subject_id))

    if grade_id.isdigit():
        posts = posts.filter(grade_level_id=int(grade_id))

    subjects = Subject.objects.all().order_by("name")
    grades = GradeLevel.objects.all().order_by("name")

    return render(
        request,
        "content/browse.html",
        {
            "posts": posts,
            "subjects": subjects,
            "grades": grades,
            "q": q,
            "subject_id": subject_id,
            "grade_id": grade_id,
        },
    )


def post_detail(request, post_id):
    post = get_object_or_404(
        DocumentPost.objects.select_related("teacher", "subject", "grade_level"),
        id=post_id,
        status=DocumentPost.Status.APPROVED,
    )

    # Only count if user is logged in
    if request.user.is_authenticated:
        # Do not count teacher's own views
        if request.user.id != post.teacher_id:
            # Create unique view once per user per post (ever)
            with transaction.atomic():
                view_obj, created = PostDetailUniqueView.objects.get_or_create(
                    user=request.user,
                    post=post,
                )

                # Only reward if this is the FIRST time
                if created:
                    today = timezone.localdate()
                    agg, _ = QualifiedViewDailyAgg.objects.get_or_create(
                        teacher_id=post.teacher_id,
                        post_id=post.id,
                        date=today,
                        defaults={"qualified_views_count": 0},
                    )
                    agg.qualified_views_count += 1
                    agg.save(update_fields=["qualified_views_count"])

    return render(request, "content/post_detail.html", {"post": post})

# content/views.py

from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone

from views_tracker.models import QualifiedViewDailyAgg
from payments.models import MonetizationSettings, EarningLedger
from payments.services import get_available_balance

from .models import DocumentPost


def _calc_post_earnings(views: int, rate_per_1000: Decimal, commission_percent: Decimal) -> Decimal:
    """
    Earnings formula:
      gross = views * (rate_per_1000 / 1000)
      net   = gross * (1 - commission_percent/100)
    """
    views = int(views or 0)
    rate_per_1000 = Decimal(rate_per_1000 or 0)
    commission_percent = Decimal(commission_percent or 0)

    gross = (Decimal(views) * (rate_per_1000 / Decimal("1000")))

    net = gross * (Decimal("1") - (commission_percent / Decimal("100")))
    # keep money clean to 2dp
    return net.quantize(Decimal("0.01"))


@login_required
def teacher_dashboard(request):
    if request.user.role != "TEACHER":
        raise Http404

    settings_obj = MonetizationSettings.get_solo()
    payout_balance = get_available_balance(request.user)

    posts = list(
        DocumentPost.objects.filter(teacher=request.user)
        .select_related("subject", "grade_level")
        .order_by("-created_at")
    )

    # ===== VIEWS =====
    # Total views across all time
    total_views = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user)
        .aggregate(total=Sum("qualified_views_count"))
        .get("total") or 0
    )

    # Today's views (daily agg uses date)
    today = timezone.localdate()
    todays_views = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user, date=today)
        .aggregate(total=Sum("qualified_views_count"))
        .get("total") or 0
    )

    # Per-post views
    per_post_views_rows = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user)
        .values("post_id")
        .annotate(total=Sum("qualified_views_count"))
    )
    per_post_views = {row["post_id"]: (row["total"] or 0) for row in per_post_views_rows}

    # Attach view + earnings to each post object for the template
    for p in posts:
        p.views_total = per_post_views.get(p.id, 0)
        p.earnings_total = _calc_post_earnings(
            views=p.views_total,
            rate_per_1000=settings_obj.rate_per_1000_views,
            commission_percent=settings_obj.platform_commission_percent,
        )

    # ===== EARNINGS =====
    # All-time earnings (net) based on ledger
    total_earnings = (
        EarningLedger.objects.filter(teacher=request.user)
        .aggregate(total=Sum("net_amount"))
        .get("total") or Decimal("0.00")
    )

    # Can request payout?
    can_request = request.user.is_teacher_verified and payout_balance >= settings_obj.minimum_payout

    return render(
        request,
        "content/teacher_dashboard.html",
        {
            "posts": posts,
            "settings_obj": settings_obj,

            "total_earnings": total_earnings,
            "payout_balance": payout_balance,
            "can_request": can_request,

            "total_views": total_views,
            "todays_views": todays_views,
        },
    )



@login_required
def upload_post(request):
    if request.user.role != "TEACHER":
        raise Http404

    if request.method == "POST":
        form = DocumentPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.teacher = request.user
            post.status = DocumentPost.Status.PENDING
            post.save()
            messages.success(request, "PDF uploaded. It is pending admin approval.")
            return redirect("content:teacher_dashboard")
    else:
        form = DocumentPostForm()

    return render(request, "content/upload_post.html", {"form": form})


@login_required
def viewer(request, post_id):
    post = get_object_or_404(
        DocumentPost.objects.select_related("teacher", "subject", "grade_level"),
        id=post_id,
        status=DocumentPost.Status.APPROVED,
    )
    return render(request, "content/viewer.html", {"post": post})


@login_required
def serve_pdf(request, post_id):
    post = get_object_or_404(
        DocumentPost,
        id=post_id,
        status=DocumentPost.Status.APPROVED,
    )

    post.pdf_file.open("rb")
    return FileResponse(
        post.pdf_file,
        content_type="application/pdf",
        as_attachment=False,
        filename=post.pdf_file.name.rsplit("/", 1)[-1],
    )
