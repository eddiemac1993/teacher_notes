from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils import timezone

from .models import User, TeacherProfile


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role & Verification", {"fields": ("role", "phone", "is_teacher_verified")}),
    )
    list_display = ("username", "email", "role", "is_teacher_verified", "is_staff", "is_active")
    list_filter = ("role", "is_teacher_verified", "is_staff", "is_active")


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "status", "verified_at", "created_at")
    list_filter = ("status",)
    search_fields = ("display_name", "user__username", "user__email", "user__phone")
    actions = ["mark_verified", "mark_rejected", "mark_pending"]

    @admin.action(description="Mark selected teachers as VERIFIED")
    def mark_verified(self, request, queryset):
        now = timezone.now()
        for profile in queryset:
            profile.status = TeacherProfile.Status.VERIFIED
            profile.verified_at = now
            profile.save(update_fields=["status", "verified_at"])
            profile.user.is_teacher_verified = True
            profile.user.save(update_fields=["is_teacher_verified"])

    @admin.action(description="Mark selected teachers as REJECTED")
    def mark_rejected(self, request, queryset):
        for profile in queryset:
            profile.status = TeacherProfile.Status.REJECTED
            profile.save(update_fields=["status"])
            profile.user.is_teacher_verified = False
            profile.user.save(update_fields=["is_teacher_verified"])

    @admin.action(description="Mark selected teachers as PENDING")
    def mark_pending(self, request, queryset):
        for profile in queryset:
            profile.status = TeacherProfile.Status.PENDING
            profile.verified_at = None
            profile.save(update_fields=["status", "verified_at"])
            profile.user.is_teacher_verified = False
            profile.user.save(update_fields=["is_teacher_verified"])
