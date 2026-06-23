from django.contrib import admin
from .models import BulletinPost


@admin.register(BulletinPost)
class BulletinPostAdmin(admin.ModelAdmin):
    list_display = ("title", "post_type", "status", "organization_name", "publish_at", "expires_at")
    list_filter = ("post_type", "status")
    search_fields = ("title", "reference_no", "organization_name", "location")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Core", {
            "fields": ("post_type", "status", "title", "summary", "body")
        }),
        ("Issuer / Contact", {
            "fields": ("organization_name", "location", "contact_email", "contact_phone")
        }),
        ("Tender Details (if applicable)", {
            "fields": ("reference_no", "submission_deadline", "attachment_pdf")
        }),
        ("Publishing", {
            "fields": ("publish_at", "expires_at", "created_by")
        }),
        ("System", {
            "fields": ("created_at", "updated_at")
        }),
    )
