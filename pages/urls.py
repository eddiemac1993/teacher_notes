from django.urls import path
from . import views

app_name = "pages"

urlpatterns = [
    path("about/", views.about, name="about"),
    path("privacy/", views.privacy, name="privacy"),
    path("teacher-guidelines/", views.teacher_guidelines, name="teacher_guidelines"),
    path("support/", views.support, name="support"),
]
