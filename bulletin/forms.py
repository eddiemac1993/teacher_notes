from django import forms
from .models import BulletinPost

class BulletinPostForm(forms.ModelForm):
    class Meta:
        model = BulletinPost
        fields = [
            "post_type",
            "status",
            "title",
            "summary",
            "body",
            "organization_name",
            "location",
            "contact_email",
            "contact_phone",
            "reference_no",
            "submission_deadline",
            "attachment_pdf",
            "publish_at",
            "expires_at",
        ]

        widgets = {
            "summary": forms.Textarea(attrs={"rows": 3}),
            "body": forms.Textarea(attrs={"rows": 8}),
            "publish_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "submission_deadline": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
