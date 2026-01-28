from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    path("teacher/payouts/", views.teacher_payouts, name="teacher_payouts"),
]
