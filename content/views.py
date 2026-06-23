from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Notification, TeacherProfile, User
from payments.models import EarningLedger, MonetizationSettings
from payments.services import get_available_balance
from views_tracker.models import QualifiedViewDailyAgg

from .forms import DocumentPostForm, MaterialReportForm, MaterialReviewForm
from .models import (
    DocumentPost,
    GradeLevel,
    MaterialReport,
    MaterialReview,
    StudentBookmark,
    StudentMaterialActivity,
    Subject,
)


def _is_staff(user):
    return user.is_authenticated and user.is_staff


def _record_activity(user, post, downloaded=False):
    if not user.is_authenticated or user.role != User.Role.STUDENT:
        return

    activity, created = StudentMaterialActivity.objects.get_or_create(
        student=user,
        post=post,
        defaults={"downloaded_at": timezone.now() if downloaded else None},
    )
    if not created:
        activity.view_count += 1
        if downloaded:
            activity.downloaded_at = timezone.now()
        activity.save(update_fields=["view_count", "downloaded_at", "last_viewed_at"])


def _attach_post_stats(posts, user=None):
    post_ids = [p.id for p in posts]
    totals = (
        QualifiedViewDailyAgg.objects.filter(post_id__in=post_ids)
        .values("post_id")
        .annotate(total=Sum("qualified_views_count"))
    )
    views_map = {row["post_id"]: row["total"] or 0 for row in totals}

    ratings = (
        MaterialReview.objects.filter(post_id__in=post_ids)
        .values("post_id")
        .annotate(avg=Avg("rating"), count=Count("id"))
    )
    ratings_map = {row["post_id"]: row for row in ratings}

    saved_ids = set()
    if user and user.is_authenticated:
        saved_ids = set(
            StudentBookmark.objects.filter(student=user, post_id__in=post_ids).values_list("post_id", flat=True)
        )

    for post in posts:
        rating = ratings_map.get(post.id, {})
        post.views_total = views_map.get(post.id, 0)
        post.rating_avg = rating.get("avg")
        post.rating_count = rating.get("count", 0)
        post.is_saved = post.id in saved_ids


def _calc_post_earnings(views: int, rate_per_1000: Decimal, commission_percent: Decimal) -> Decimal:
    views = int(views or 0)
    rate_per_1000 = Decimal(rate_per_1000 or 0)
    commission_percent = Decimal(commission_percent or 0)
    gross = Decimal(views) * (rate_per_1000 / Decimal("1000"))
    net = gross * (Decimal("1") - (commission_percent / Decimal("100")))
    return net.quantize(Decimal("0.01"))


def home(request):
    featured_posts = list(
        DocumentPost.objects.filter(status=DocumentPost.Status.APPROVED, is_featured=True)
        .select_related("teacher", "subject", "grade_level")[:6]
    )
    posts = list(
        DocumentPost.objects.filter(status=DocumentPost.Status.APPROVED)
        .select_related("teacher", "subject", "grade_level")[:20]
    )
    _attach_post_stats(featured_posts, request.user)
    _attach_post_stats(posts, request.user)
    return render(request, "content/home.html", {"featured_posts": featured_posts, "posts": posts})


def browse(request):
    q = (request.GET.get("q") or "").strip()
    subject_id = request.GET.get("subject") or ""
    grade_id = request.GET.get("grade") or ""

    posts = (
        DocumentPost.objects.filter(status=DocumentPost.Status.APPROVED)
        .select_related("teacher", "subject", "grade_level")
        .order_by("-is_featured", "-created_at")
    )

    if q:
        posts = posts.filter(
            Q(title__icontains=q)
            | Q(topic__icontains=q)
            | Q(description__icontains=q)
            | Q(subject__name__icontains=q)
            | Q(grade_level__name__icontains=q)
            | Q(teacher__username__icontains=q)
            | Q(teacher__teacher_profile__display_name__icontains=q)
        ).distinct()

    if subject_id.isdigit():
        posts = posts.filter(subject_id=int(subject_id))

    if grade_id.isdigit():
        posts = posts.filter(grade_level_id=int(grade_id))

    subjects = Subject.objects.all().order_by("name")
    grades = GradeLevel.objects.all().order_by("name")
    paginator = Paginator(posts, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    page_posts = list(page_obj.object_list)
    _attach_post_stats(page_posts, request.user)

    return render(
        request,
        "content/browse.html",
        {
            "posts": page_posts,
            "page_obj": page_obj,
            "result_count": paginator.count,
            "subjects": subjects,
            "grades": grades,
            "q": q,
            "subject_id": subject_id,
            "grade_id": grade_id,
        },
    )


def search_suggestions(request):
    q = (request.GET.get("q") or "").strip()
    suggestions = []
    if q:
        titles = DocumentPost.objects.filter(status=DocumentPost.Status.APPROVED, title__icontains=q).values_list(
            "title", flat=True
        )[:5]
        topics = DocumentPost.objects.filter(status=DocumentPost.Status.APPROVED, topic__icontains=q).values_list(
            "topic", flat=True
        )[:5]
        subjects = Subject.objects.filter(name__icontains=q).values_list("name", flat=True)[:5]
        suggestions = list(dict.fromkeys([*titles, *topics, *subjects]))[:8]
    return JsonResponse({"suggestions": suggestions})


def learning_paths(request):
    subjects = (
        Subject.objects.annotate(material_count=Count("documentpost", filter=Q(documentpost__status=DocumentPost.Status.APPROVED)))
        .filter(material_count__gt=0)
        .order_by("name")
    )
    grades = GradeLevel.objects.annotate(
        material_count=Count("documentpost", filter=Q(documentpost__status=DocumentPost.Status.APPROVED))
    ).filter(material_count__gt=0)
    return render(request, "content/learning_paths.html", {"subjects": subjects, "grades": grades})


def post_detail(request, post_id):
    post = get_object_or_404(
        DocumentPost.objects.select_related("teacher", "subject", "grade_level"),
        id=post_id,
        status=DocumentPost.Status.APPROVED,
    )
    _record_activity(request.user, post)
    _attach_post_stats([post], request.user)
    review_form = MaterialReviewForm()
    report_form = MaterialReportForm()
    user_review = None
    if request.user.is_authenticated:
        user_review = MaterialReview.objects.filter(student=request.user, post=post).first()
        if user_review:
            review_form = MaterialReviewForm(instance=user_review)
    reviews = post.reviews.select_related("student")[:10]
    return render(
        request,
        "content/post_detail.html",
        {"post": post, "review_form": review_form, "report_form": report_form, "reviews": reviews, "user_review": user_review},
    )


@login_required
@require_POST
def toggle_bookmark(request, post_id):
    if request.user.role != User.Role.STUDENT:
        messages.error(request, "Only student accounts can save materials.")
        return redirect("content:post_detail", post_id=post_id)
    post = get_object_or_404(DocumentPost, id=post_id, status=DocumentPost.Status.APPROVED)
    bookmark, created = StudentBookmark.objects.get_or_create(student=request.user, post=post)
    if created:
        messages.success(request, "Saved to your library.")
    else:
        bookmark.delete()
        messages.success(request, "Removed from your library.")
    return redirect(request.POST.get("next") or reverse("content:post_detail", args=[post_id]))


@login_required
def my_library(request):
    if request.user.role != User.Role.STUDENT:
        raise Http404
    bookmarks = StudentBookmark.objects.filter(student=request.user).select_related("post", "post__subject", "post__grade_level")
    recent = StudentMaterialActivity.objects.filter(student=request.user).select_related("post", "post__subject", "post__grade_level")[:12]
    downloads = (
        StudentMaterialActivity.objects.filter(student=request.user, downloaded_at__isnull=False)
        .select_related("post", "post__subject", "post__grade_level")[:12]
    )
    return render(request, "content/my_library.html", {"bookmarks": bookmarks, "recent": recent, "downloads": downloads})


@login_required
@require_POST
def submit_review(request, post_id):
    if request.user.role != User.Role.STUDENT:
        messages.error(request, "Only students can review materials.")
        return redirect("content:post_detail", post_id=post_id)
    post = get_object_or_404(DocumentPost, id=post_id, status=DocumentPost.Status.APPROVED)
    review = MaterialReview.objects.filter(student=request.user, post=post).first()
    form = MaterialReviewForm(request.POST, instance=review)
    if form.is_valid():
        saved = form.save(commit=False)
        saved.student = request.user
        saved.post = post
        saved.save()
        messages.success(request, "Thanks for reviewing this material.")
    else:
        messages.error(request, "Please choose a rating before submitting your review.")
    return redirect("content:post_detail", post_id=post_id)


@login_required
@require_POST
def report_material(request, post_id):
    if request.user.role != User.Role.STUDENT:
        messages.error(request, "Only students can report materials.")
        return redirect("content:post_detail", post_id=post_id)
    post = get_object_or_404(DocumentPost, id=post_id, status=DocumentPost.Status.APPROVED)
    form = MaterialReportForm(request.POST)
    if form.is_valid():
        report = form.save(commit=False)
        report.student = request.user
        report.post = post
        report.save()
        messages.success(request, "Report sent to admins for review.")
    else:
        messages.error(request, "Please choose a reason for the report.")
    return redirect("content:post_detail", post_id=post_id)


def teacher_profile(request, username):
    teacher = get_object_or_404(User.objects.filter(role=User.Role.TEACHER), username=username)
    posts = list(
        DocumentPost.objects.filter(teacher=teacher, status=DocumentPost.Status.APPROVED)
        .select_related("subject", "grade_level")
        .order_by("-created_at")
    )
    _attach_post_stats(posts, request.user)
    total_views = sum(p.views_total for p in posts)
    rating_values = [p.rating_avg for p in posts if p.rating_avg]
    rating_avg = sum(rating_values) / len(rating_values) if rating_values else None
    badges = []
    if teacher.is_teacher_verified:
        badges.append("Verified Teacher")
    if total_views >= 1000:
        badges.append("1000+ Views")
    if posts:
        badges.append(f"{len(posts)} Material{'s' if len(posts) != 1 else ''}")
    return render(
        request,
        "content/teacher_profile.html",
        {"teacher_obj": teacher, "posts": posts, "total_views": total_views, "rating_avg": rating_avg, "badges": badges},
    )


@login_required
def teacher_dashboard(request):
    if request.user.role != User.Role.TEACHER:
        raise Http404

    settings_obj = MonetizationSettings.get_solo()
    payout_balance = get_available_balance(request.user)
    posts = list(
        DocumentPost.objects.filter(teacher=request.user)
        .select_related("subject", "grade_level")
        .order_by("-created_at")
    )

    total_views = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user).aggregate(total=Sum("qualified_views_count")).get("total") or 0
    )
    today = timezone.localdate()
    todays_views = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user, date=today)
        .aggregate(total=Sum("qualified_views_count"))
        .get("total")
        or 0
    )
    per_post_views_rows = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user).values("post_id").annotate(total=Sum("qualified_views_count"))
    )
    per_post_views = {row["post_id"]: row["total"] or 0 for row in per_post_views_rows}
    for post in posts:
        post.views_total = per_post_views.get(post.id, 0)
        post.earnings_total = _calc_post_earnings(
            views=post.views_total,
            rate_per_1000=settings_obj.rate_per_1000_views,
            commission_percent=settings_obj.platform_commission_percent,
        )

    total_earnings = (
        EarningLedger.objects.filter(teacher=request.user).aggregate(total=Sum("net_amount")).get("total") or Decimal("0.00")
    )
    can_request = request.user.is_teacher_verified and payout_balance >= settings_obj.minimum_payout
    notifications = request.user.notifications.all()[:6]

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
            "notifications": notifications,
        },
    )


@login_required
def upload_post(request):
    if request.user.role != User.Role.TEACHER:
        raise Http404
    if not request.user.is_teacher_verified:
        messages.error(request, "Your teacher account must be approved by an admin before you can upload materials.")
        return redirect("content:teacher_dashboard")

    if request.method == "POST":
        form = DocumentPostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.teacher = request.user
            is_draft = request.POST.get("action") == "draft"
            post.status = DocumentPost.Status.DRAFT if is_draft else DocumentPost.Status.PENDING
            post.save()
            if is_draft:
                messages.success(request, "Draft saved. Submit it when you are ready for admin review.")
            else:
                messages.success(request, "Material submitted. It is pending admin approval.")
            return redirect("content:teacher_dashboard")
    else:
        form = DocumentPostForm()

    return render(request, "content/upload_post.html", {"form": form, "mode": "upload"})


@login_required
def edit_post(request, post_id):
    post = get_object_or_404(DocumentPost, id=post_id, teacher=request.user)
    if request.user.role != User.Role.TEACHER:
        raise Http404
    if post.status == DocumentPost.Status.APPROVED:
        messages.error(request, "Approved materials cannot be edited yet. Contact admin if a correction is needed.")
        return redirect("content:teacher_dashboard")

    if request.method == "POST":
        form = DocumentPostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated = form.save(commit=False)
            is_draft = request.POST.get("action") == "draft"
            updated.status = DocumentPost.Status.DRAFT if is_draft else DocumentPost.Status.PENDING
            if not is_draft:
                updated.rejection_reason = ""
            updated.save()
            if is_draft:
                messages.success(request, "Draft updated.")
            else:
                messages.success(request, "Material updated and resubmitted for approval.")
            return redirect("content:teacher_dashboard")
    else:
        form = DocumentPostForm(instance=post)
    return render(request, "content/upload_post.html", {"form": form, "mode": "edit", "post": post})


@login_required
def viewer(request, post_id):
    post = get_object_or_404(
        DocumentPost.objects.select_related("teacher", "subject", "grade_level"),
        id=post_id,
        status=DocumentPost.Status.APPROVED,
    )
    _record_activity(request.user, post)
    return render(request, "content/viewer.html", {"post": post})


@login_required
def serve_pdf(request, post_id):
    post = get_object_or_404(DocumentPost, id=post_id, status=DocumentPost.Status.APPROVED)
    _record_activity(request.user, post, downloaded=True)
    post.pdf_file.open("rb")
    return FileResponse(
        post.pdf_file,
        content_type="application/pdf",
        as_attachment=False,
        filename=post.pdf_file.name.rsplit("/", 1)[-1],
    )


@user_passes_test(_is_staff)
def admin_queue(request):
    pending_teachers = TeacherProfile.objects.filter(status=TeacherProfile.Status.PENDING).select_related("user")
    pending_posts = DocumentPost.objects.filter(status=DocumentPost.Status.PENDING).select_related("teacher", "subject", "grade_level")
    open_reports = MaterialReport.objects.exclude(status=MaterialReport.Status.RESOLVED).select_related("student", "post")
    return render(
        request,
        "content/admin_queue.html",
        {"pending_teachers": pending_teachers, "pending_posts": pending_posts, "open_reports": open_reports},
    )


@user_passes_test(_is_staff)
@require_POST
def admin_approve_teacher(request, profile_id):
    profile = get_object_or_404(TeacherProfile.objects.select_related("user"), id=profile_id)
    profile.status = TeacherProfile.Status.VERIFIED
    profile.verified_at = timezone.now()
    profile.admin_note = ""
    profile.save(update_fields=["status", "verified_at", "admin_note"])
    profile.user.is_teacher_verified = True
    profile.user.save(update_fields=["is_teacher_verified"])
    Notification.objects.create(
        user=profile.user,
        kind=Notification.Kind.APPROVAL,
        title="Teacher account approved",
        message="Your account is approved. You can now upload materials and request payouts when eligible.",
    )
    messages.success(request, f"Approved {profile.display_name}.")
    return redirect("content:admin_queue")


@user_passes_test(_is_staff)
@require_POST
def admin_reject_teacher(request, profile_id):
    profile = get_object_or_404(TeacherProfile.objects.select_related("user"), id=profile_id)
    note = (request.POST.get("note") or "").strip()
    profile.status = TeacherProfile.Status.REJECTED
    profile.verified_at = None
    profile.admin_note = note
    profile.save(update_fields=["status", "verified_at", "admin_note"])
    profile.user.is_teacher_verified = False
    profile.user.save(update_fields=["is_teacher_verified"])
    Notification.objects.create(
        user=profile.user,
        kind=Notification.Kind.APPROVAL,
        title="Teacher account rejected",
        message=note or "Your teacher account was rejected. Please contact support for more details.",
    )
    messages.success(request, f"Rejected {profile.display_name}.")
    return redirect("content:admin_queue")


@user_passes_test(_is_staff)
@require_POST
def admin_approve_post(request, post_id):
    post = get_object_or_404(DocumentPost.objects.select_related("teacher"), id=post_id)
    post.status = DocumentPost.Status.APPROVED
    post.rejection_reason = ""
    post.save(update_fields=["status", "rejection_reason"])
    Notification.objects.create(
        user=post.teacher,
        kind=Notification.Kind.MATERIAL,
        title="Material approved",
        message=f"Your material '{post.title}' is now live for students.",
    )
    messages.success(request, f"Approved {post.title}.")
    return redirect("content:admin_queue")


@user_passes_test(_is_staff)
@require_POST
def admin_reject_post(request, post_id):
    post = get_object_or_404(DocumentPost.objects.select_related("teacher"), id=post_id)
    reason = (request.POST.get("reason") or "").strip()
    post.status = DocumentPost.Status.REJECTED
    post.rejection_reason = reason
    post.save(update_fields=["status", "rejection_reason"])
    Notification.objects.create(
        user=post.teacher,
        kind=Notification.Kind.MATERIAL,
        title="Material needs changes",
        message=reason or f"Your material '{post.title}' was rejected. Please review and resubmit.",
    )
    messages.success(request, f"Rejected {post.title}.")
    return redirect("content:admin_queue")
