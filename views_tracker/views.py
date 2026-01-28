# views_tracker/views.py

import hashlib

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from content.models import DocumentPost
from .models import DocumentOpenSession, QualifiedViewDailyAgg


def _hash_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _get_client_ip(request) -> str:
    # MVP: if behind proxy later, handle X-Forwarded-For properly
    return request.META.get("REMOTE_ADDR", "") or ""


def _qualified_in_last_24h(user_id: int, post_id: int) -> bool:
    cutoff = timezone.now() - timezone.timedelta(hours=24)
    return DocumentOpenSession.objects.filter(
        user_id=user_id,
        post_id=post_id,
        is_qualified=True,
        qualified_at__gte=cutoff,
    ).exists()


@login_required
@require_POST
def start(request):
    post_id = request.POST.get("post_id")
    if not (post_id and str(post_id).isdigit()):
        return JsonResponse({"ok": False, "error": "Invalid post_id"}, status=400)

    post = get_object_or_404(DocumentPost, id=int(post_id), status=DocumentPost.Status.APPROVED)

    # Do not count teacher's own views
    if request.user.id == post.teacher_id:
        return JsonResponse({"ok": False, "error": "Self views do not count"}, status=200)

    # One qualified view per user per document per 24 hours
    already_qualified_24h = _qualified_in_last_24h(request.user.id, post.id)
    now = timezone.now()

    # Create a session for today (or reuse)
    today = timezone.localdate()
    session, created = DocumentOpenSession.objects.get_or_create(
        user=request.user,
        post=post,
        date=today,
        defaults={
            # Use the same fields your heartbeat uses
            "seconds_accumulated": 0,
            "interacted": True,          # Auto-interaction
            "is_qualified": False,       # we set below based on 24h rule
            "qualified_at": None,
            "last_heartbeat_at": now,
            "ip_hash": _hash_text(_get_client_ip(request)),
            "ua_hash": _hash_text(request.META.get("HTTP_USER_AGENT", "")),
        },
    )

    # Always update heartbeat anchor on start
    session.last_heartbeat_at = now

    qualified_now = False

    # Auto-qualify on open (only if not already qualified in last 24h)
    if (not already_qualified_24h) and (not session.is_qualified):
        session.interacted = True
        session.is_qualified = True
        session.qualified_at = now
        qualified_now = True

        # Update daily aggregate immediately (so earnings work)
        agg, _created = QualifiedViewDailyAgg.objects.get_or_create(
            post_id=post.id,
            date=today,
            defaults={"teacher_id": post.teacher_id, "qualified_views_count": 0},
        )
        agg.qualified_views_count += 1
        agg.save(update_fields=["qualified_views_count"])

    session.save(update_fields=["last_heartbeat_at", "interacted", "is_qualified", "qualified_at"])

    return JsonResponse(
        {
            "ok": True,
            "session_id": session.id,
            "seconds": session.seconds_accumulated,
            "interacted": session.interacted,
            "qualified": session.is_qualified,
            "qualified_now": qualified_now,
        }
    )


@login_required
@require_POST
def interact(request):
    session_id = request.POST.get("session_id")
    if not (session_id and str(session_id).isdigit()):
        return JsonResponse({"ok": False, "error": "Invalid session_id"}, status=400)

    session = DocumentOpenSession.objects.select_related("post", "post__teacher").filter(
        id=int(session_id), user=request.user
    ).first()
    if not session:
        raise Http404

    if not session.interacted:
        session.interacted = True
        session.save(update_fields=["interacted"])

    return JsonResponse({"ok": True})


@login_required
@require_POST
def heartbeat(request):
    session_id = request.POST.get("session_id")
    if not (session_id and str(session_id).isdigit()):
        return JsonResponse({"ok": False, "error": "Invalid session_id"}, status=400)

    session = DocumentOpenSession.objects.select_related("post", "post__teacher").filter(
        id=int(session_id), user=request.user
    ).first()
    if not session:
        raise Http404

    # If post is no longer approved, do not track
    if session.post.status != DocumentPost.Status.APPROVED:
        return JsonResponse({"ok": True, "qualified": False, "seconds": session.seconds_accumulated})

    now = timezone.now()
    delta = (now - session.last_heartbeat_at).total_seconds()

    # Guardrails
    if delta < 0:
        delta = 0
    if delta > 10:
        delta = 10

    session.seconds_accumulated = session.seconds_accumulated + int(delta)
    session.last_heartbeat_at = now
    session.save(update_fields=["seconds_accumulated", "last_heartbeat_at"])

    return JsonResponse(
        {
            "ok": True,
            "qualified": session.is_qualified,
            "qualified_now": False,
            "seconds": session.seconds_accumulated,
            "interacted": session.interacted,
        }
    )
