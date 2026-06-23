from django import forms
from .models import DocumentPost, MaterialReport, MaterialReview


class DocumentPostForm(forms.ModelForm):
    class Meta:
        model = DocumentPost
        fields = [
            "title",
            "subject",
            "grade_level",
            "topic",
            "description",
            "exam_year",
            "language",
            "has_answers",
            "pdf_file",
            "external_video_url",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "title": "e.g. Grade 9 Algebra Revision Notes",
            "topic": "Main concepts, keywords, or syllabus area",
            "description": "Short summary of what learners will find inside",
            "exam_year": "Optional, e.g. 2025",
            "language": "English",
            "external_video_url": "Optional YouTube or Vimeo lesson link",
        }
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "h-4 w-4 rounded border-slate-300 text-indigo-600"})
                continue
            field.widget.attrs.update(
                {
                    "class": "form-control",
                    "placeholder": placeholders.get(name, ""),
                }
            )

    def clean_external_video_url(self):
        url = (self.cleaned_data.get("external_video_url") or "").strip()
        if not url:
            return ""
        allowed = ("youtube.com", "youtu.be", "vimeo.com")
        if not any(domain in url.lower() for domain in allowed):
            raise forms.ValidationError("Use a YouTube or Vimeo link for video lessons.")
        return url


class MaterialReviewForm(forms.ModelForm):
    class Meta:
        model = MaterialReview
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(choices=[(i, f"{i} star{'s' if i != 1 else ''}") for i in range(5, 0, -1)]),
            "comment": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})


class MaterialReportForm(forms.ModelForm):
    class Meta:
        model = MaterialReport
        fields = ["reason", "note"]
        widgets = {"note": forms.Textarea(attrs={"rows": 3, "placeholder": "Tell the admin what needs attention."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({"class": "form-control"})
