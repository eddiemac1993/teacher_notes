from django import forms
from .models import DocumentPost


class DocumentPostForm(forms.ModelForm):
    class Meta:
        model = DocumentPost
        fields = ["title", "subject", "grade_level", "topic", "pdf_file", "external_video_url"]

    def clean_external_video_url(self):
        url = (self.cleaned_data.get("external_video_url") or "").strip()
        if not url:
            return ""
        # Very light allowlist for MVP (tighten later)
        allowed = ("youtube.com", "youtu.be", "vimeo.com")
        if not any(domain in url.lower() for domain in allowed):
            # still allow other links if you want; if not, enforce here
            return url
        return url
