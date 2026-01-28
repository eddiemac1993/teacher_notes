from django.contrib import admin
from .models import Subject, GradeLevel, DocumentPost


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(GradeLevel)
class GradeLevelAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(DocumentPost)
class DocumentPostAdmin(admin.ModelAdmin):
    list_display = ("title", "teacher", "subject", "grade_level", "status", "created_at")
    list_filter = ("status", "subject", "grade_level")
    search_fields = ("title", "topic", "teacher__username", "teacher__email")
    readonly_fields = ("created_at",)

    actions = ["approve_posts", "reject_posts"]

    @admin.action(description="Approve selected posts")
    def approve_posts(self, request, queryset):
        queryset.update(status=DocumentPost.Status.APPROVED, rejection_reason="")

    @admin.action(description="Reject selected posts")
    def reject_posts(self, request, queryset):
        queryset.update(status=DocumentPost.Status.REJECTED)
