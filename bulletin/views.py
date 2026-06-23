from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import BulletinPostForm
from .models import BulletinPost


def _is_staff_user(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def bulletin_home(request):
    q = (request.GET.get("q") or "").strip()
    post_type = (request.GET.get("type") or "").strip()
    status = (request.GET.get("status") or "").strip()

    posts = BulletinPost.objects.all()

    now = timezone.now()

    # Public can only see: published + not expired + not draft
    posts = posts.filter(
        publish_at__lte=now
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).exclude(
        status=BulletinPost.Status.DRAFT
    )

    if post_type in dict(BulletinPost.PostType.choices):
        posts = posts.filter(post_type=post_type)

    # Only allow filtering by status that makes sense for public,
    # but keep your current logic (it will still work)
    if status in dict(BulletinPost.Status.choices):
        posts = posts.filter(status=status)

    if q:
        posts = posts.filter(
            Q(title__icontains=q)
            | Q(summary__icontains=q)
            | Q(body__icontains=q)
            | Q(reference_no__icontains=q)
            | Q(organization_name__icontains=q)
            | Q(location__icontains=q)
        )

    posts = posts.select_related("author")[:100]

    return render(
        request,
        "bulletin/home.html",
        {
            "posts": posts,
            "q": q,
            "post_type": post_type,
            "status": status,
            "type_choices": BulletinPost.PostType.choices,
            "status_choices": BulletinPost.Status.choices,
        },
    )


def bulletin_detail(request, pk: int):
    post = get_object_or_404(BulletinPost.objects.select_related("author"), pk=pk)

    # If not staff, block draft/unpublished/expired
    if not _is_staff_user(request.user):
        now = timezone.now()
        if (
            post.status == BulletinPost.Status.DRAFT
            or post.publish_at > now
            or (post.expires_at and post.expires_at <= now)
        ):
            raise Http404

    return render(request, "bulletin/detail.html", {"post": post})


@login_required
@user_passes_test(_is_staff_user)
def bulletin_create(request):
    if request.method == "POST":
        form = BulletinPostForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)

            # NEW: author field (replaces created_by)
            obj.author = request.user

            # Safety: set publish_at if blank
            if not obj.publish_at:
                obj.publish_at = timezone.now()

            obj.save()
            messages.success(request, "Bulletin post created successfully.")
            return redirect("bulletin:home")
    else:
        form = BulletinPostForm()

    return render(request, "bulletin/create.html", {"form": form})
