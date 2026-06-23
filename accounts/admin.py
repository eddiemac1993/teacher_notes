from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils import timezone

from .models import Notification, TeacherProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Role & Verification", {"fields": ("role", "phone", "is_teacher_verified")}),
    )
    list_display = ("username", "email", "role", "is_teacher_verified", "is_staff", "is_active")
    list_filter = ("role", "is_teacher_verified", "is_staff", "is_active")
    actions = ["approve_teachers", "unapprove_teachers"]

    @admin.action(description="Approve selected teacher users")
    def approve_teachers(self, request, queryset):
        now = timezone.now()
        for user in queryset.filter(role=User.Role.TEACHER):
            user.is_teacher_verified = True
            user.save(update_fields=["is_teacher_verified"])
            if hasattr(user, "teacher_profile"):
                user.teacher_profile.status = TeacherProfile.Status.VERIFIED
                user.teacher_profile.verified_at = now
                user.teacher_profile.save(update_fields=["status", "verified_at"])

    @admin.action(description="Unapprove selected teacher users")
    def unapprove_teachers(self, request, queryset):
        for user in queryset.filter(role=User.Role.TEACHER):
            user.is_teacher_verified = False
            user.save(update_fields=["is_teacher_verified"])
            if hasattr(user, "teacher_profile"):
                user.teacher_profile.status = TeacherProfile.Status.PENDING
                user.teacher_profile.verified_at = None
                user.teacher_profile.save(update_fields=["status", "verified_at"])


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "status", "verified_at", "created_at")
    list_filter = ("status",)
    search_fields = ("display_name", "user__username", "user__email", "user__phone")
    actions = ["mark_verified", "mark_rejected", "mark_pending"]

    def save_model(self, request, obj, form, change):
        if obj.status == TeacherProfile.Status.VERIFIED and obj.verified_at is None:
            obj.verified_at = timezone.now()
        if obj.status != TeacherProfile.Status.VERIFIED:
            obj.verified_at = None
        super().save_model(request, obj, form, change)
        obj.user.is_teacher_verified = obj.status == TeacherProfile.Status.VERIFIED
        obj.user.save(update_fields=["is_teacher_verified"])

    @admin.action(description="Mark selected teachers as VERIFIED")
    def mark_verified(self, request, queryset):
        now = timezone.now()
        for profile in queryset:
            profile.status = TeacherProfile.Status.VERIFIED
            profile.verified_at = now
            profile.save(update_fields=["status", "verified_at"])
            profile.user.is_teacher_verified = True
            profile.user.save(update_fields=["is_teacher_verified"])
            Notification.objects.create(
                user=profile.user,
                kind=Notification.Kind.APPROVAL,
                title="Teacher account approved",
                message="Your teacher account has been approved. You can now upload materials and earn from qualified views.",
            )

    @admin.action(description="Mark selected teachers as REJECTED")
    def mark_rejected(self, request, queryset):
        for profile in queryset:
            profile.status = TeacherProfile.Status.REJECTED
            profile.save(update_fields=["status"])
            profile.user.is_teacher_verified = False
            profile.user.save(update_fields=["is_teacher_verified"])
            Notification.objects.create(
                user=profile.user,
                kind=Notification.Kind.APPROVAL,
                title="Teacher account rejected",
                message=profile.admin_note or "Your teacher account was rejected. Please contact support for details.",
            )

    @admin.action(description="Mark selected teachers as PENDING")
    def mark_pending(self, request, queryset):
        for profile in queryset:
            profile.status = TeacherProfile.Status.PENDING
            profile.verified_at = None
            profile.save(update_fields=["status", "verified_at"])
            profile.user.is_teacher_verified = False
            profile.user.save(update_fields=["is_teacher_verified"])


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "kind", "is_read", "created_at")
    list_filter = ("kind", "is_read")
    search_fields = ("user__username", "title", "message")
