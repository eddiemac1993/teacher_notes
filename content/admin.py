from django.contrib import admin
from .models import (
    DocumentPost,
    GradeLevel,
    MaterialReport,
    MaterialReview,
    StudentBookmark,
    StudentMaterialActivity,
    Subject,
)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(DocumentPost)
class DocumentPostAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "subject", "grade_level", "status", "is_featured", "created_at")
    list_filter = ("status", "is_featured", "subject", "grade_level")
    search_fields = ("title", "topic", "teacher__username", "teacher__email")
    readonly_fields = ("created_at",)

    actions = ["approve_posts", "reject_posts", "feature_posts", "unfeature_posts"]

    @admin.action(description="Approve selected posts")
    def approve_posts(self, request, queryset):
        queryset.update(status=DocumentPost.Status.APPROVED, rejection_reason="")

    @admin.action(description="Reject selected posts")
    def reject_posts(self, request, queryset):
        queryset.update(status=DocumentPost.Status.REJECTED)

    @admin.action(description="Feature selected posts on the homepage")
    def feature_posts(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description="Remove selected posts from featured")
    def unfeature_posts(self, request, queryset):
        queryset.update(is_featured=False)


@admin.register(StudentBookmark)
class StudentBookmarkAdmin(admin.ModelAdmin):
    list_display = ("student", "post", "created_at")
    search_fields = ("student__username", "post__title")


@admin.register(StudentMaterialActivity)
class StudentMaterialActivityAdmin(admin.ModelAdmin):
    list_display = ("student", "post", "view_count", "last_viewed_at", "downloaded_at")
    search_fields = ("student__username", "post__title")


@admin.register(MaterialReview)
class MaterialReviewAdmin(admin.ModelAdmin):
    list_display = ("post", "student", "rating", "updated_at")
    list_filter = ("rating",)
    search_fields = ("post__title", "student__username", "comment")


@admin.register(MaterialReport)
class MaterialReportAdmin(admin.ModelAdmin):
    list_display = ("post", "student", "reason", "status", "created_at")
    list_filter = ("reason", "status")
    search_fields = ("post__title", "student__username", "note")
    actions = ["mark_reviewing", "mark_resolved"]

    @admin.action(description="Mark selected reports as reviewing")
    def mark_reviewing(self, request, queryset):
        queryset.update(status=MaterialReport.Status.REVIEWING)

    @admin.action(description="Mark selected reports as resolved")
    def mark_resolved(self, request, queryset):
        queryset.update(status=MaterialReport.Status.RESOLVED)
