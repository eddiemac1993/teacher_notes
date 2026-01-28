from django.conf import settings
from django.db import models
from django.utils import timezone


class DocumentOpenSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey("content.DocumentPost", on_delete=models.CASCADE)

    started_at = models.DateTimeField(default=timezone.now)
    last_heartbeat_at = models.DateTimeField(default=timezone.now)

    seconds_accumulated = models.PositiveIntegerField(default=0)
    interacted = models.BooleanField(default=False)

    is_qualified = models.BooleanField(default=False)
    qualified_at = models.DateTimeField(blank=True, null=True)

    # Anti-fraud signals (MVP)
    ip_hash = models.CharField(max_length=64, blank=True)
    user_agent_hash = models.CharField(max_length=64, blank=True)

    # For 24h uniqueness convenience
    day_key = models.DateField(default=timezone.localdate)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "post", "qualified_at"]),
            models.Index(fields=["post", "day_key"]),
        ]

    def __str__(self):
        return f"Session user={self.user_id} post={self.post_id} qualified={self.is_qualified}"


class QualifiedViewDailyAgg(models.Model):
    post = models.ForeignKey("content.DocumentPost", on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    date = models.DateField()
    qualified_views_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("post", "date")
        indexes = [models.Index(fields=["teacher", "date"])]

    def __str__(self):
        return f"Agg post={self.post_id} date={self.date} views={self.qualified_views_count}"

class PostDetailUniqueView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey("content.DocumentPost", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")
        indexes = [
            models.Index(fields=["post", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"DetailView user={self.user_id} post={self.post_id}"
