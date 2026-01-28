from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    path("", views.home, name="home"),
    path("materials/", views.browse, name="browse"),
    path("materials/<int:post_id>/", views.post_detail, name="post_detail"),

    path("viewer/<int:post_id>/", views.viewer, name="viewer"),
    path("pdf/<int:post_id>/file/", views.serve_pdf, name="serve_pdf"),

    path("teacher/dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/upload/", views.upload_post, name="upload_post"),
]
