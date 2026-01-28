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

@login_required
def teacher_dashboard(request):
    if request.user.role != "TEACHER":
        raise Http404

    posts = list(
        DocumentPost.objects.filter(teacher=request.user)
        .select_related("subject", "grade_level")
    )

    # Total qualified views across ALL teacher posts (all time)
    total_qualified_views = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user)
        .aggregate(total=Sum("qualified_views_count"))
        .get("total")
        or 0
    )

    # Qualified views today
    today = timezone.localdate()
    qualified_views_today = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user, date=today)
        .aggregate(total=Sum("qualified_views_count"))
        .get("total")
        or 0
    )

    # Per-post qualified view totals (all time)
    per_post = (
        QualifiedViewDailyAgg.objects.filter(teacher=request.user)
        .values("post_id")
        .annotate(total=Sum("qualified_views_count"))
    )
    per_post_map = {row["post_id"]: (row["total"] or 0) for row in per_post}

    # Attach computed value directly to each post so the template can do: {{ p.qualified_views_total }}
    for p in posts:
        p.qualified_views_total = per_post_map.get(p.id, 0)

    return render(
        request,
        "content/teacher_dashboard.html",
        {
            "posts": posts,
            "total_qualified_views": total_qualified_views,
            "qualified_views_today": qualified_views_today,
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
