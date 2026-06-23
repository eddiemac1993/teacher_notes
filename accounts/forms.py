from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError

from .models import User, TeacherProfile


class TeacherRegisterForm(UserCreationForm):
    display_name = forms.CharField(max_length=120)
    phone = forms.CharField(max_length=20, required=True, help_text="Example: +26097xxxxxxx")
    payout_mobile_money_number = forms.CharField(max_length=20, required=False)
    payout_network = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "phone", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "display_name": "e.g. Ms. Banda",
            "username": "Choose a username",
            "email": "you@example.com",
            "phone": "+26097xxxxxxx",
            "payout_mobile_money_number": "+26097xxxxxxx",
            "payout_network": "Airtel, MTN, or Zamtel",
            "password1": "Create a strong password",
            "password2": "Repeat your password",
        }
        for name, field in self.fields.items():
            field.widget.attrs.update(
                {
                    "class": "form-control",
                    "placeholder": placeholders.get(name, ""),
                }
            )

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            raise ValidationError("Phone number is required.")
        # very light validation; stricter can come later
        if len(phone) < 9:
            raise ValidationError("Phone number looks too short.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.TEACHER
        user.phone = self.cleaned_data.get("phone")
        user.is_teacher_verified = False  # admin must verify
        if commit:
            user.save()

            TeacherProfile.objects.create(
                user=user,
                display_name=self.cleaned_data.get("display_name"),
                payout_mobile_money_number=self.cleaned_data.get("payout_mobile_money_number", ""),
                payout_network=self.cleaned_data.get("payout_network", ""),
                status=TeacherProfile.Status.PENDING,
            )
        return user


class StudentRegisterForm(UserCreationForm):
    phone = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ("username", "email", "phone", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "username": "Choose a username",
            "email": "you@example.com",
            "phone": "+26097xxxxxxx",
            "password1": "Create a strong password",
            "password2": "Repeat your password",
        }
        for name, field in self.fields.items():
            field.widget.attrs.update(
                {
                    "class": "form-control",
                    "placeholder": placeholders.get(name, ""),
                }
            )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.STUDENT
        user.phone = self.cleaned_data.get("phone")
        user.is_teacher_verified = False
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Username"}
        )
        self.fields["password"].widget.attrs.update(
            {"class": "form-control", "placeholder": "Password"}
        )
