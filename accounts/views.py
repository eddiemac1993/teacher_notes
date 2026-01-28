from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import TeacherRegisterForm, StudentRegisterForm, LoginForm


def register_teacher(request):
    if request.user.is_authenticated:
        return redirect("content:home")

    if request.method == "POST":
        form = TeacherRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "Account created. Your teacher profile is pending verification. You can browse, but earnings start after admin verification.",
            )
            return redirect("content:home")
    else:
        form = TeacherRegisterForm()

    return render(request, "accounts/register_teacher.html", {"form": form})


def register_student(request):
    if request.user.is_authenticated:
        return redirect("content:home")

    if request.method == "POST":
        form = StudentRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Student account created successfully.")
            return redirect("content:home")
    else:
        form = StudentRegisterForm()

    return render(request, "accounts/register_student.html", {"form": form})


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("content:home")
