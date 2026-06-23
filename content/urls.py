from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    path("", views.home, name="home"),
    path("materials/", views.browse, name="browse"),
    path("materials/suggestions/", views.search_suggestions, name="search_suggestions"),
    path("learning-paths/", views.learning_paths, name="learning_paths"),
    path("materials/<int:post_id>/", views.post_detail, name="post_detail"),
    path("materials/<int:post_id>/bookmark/", views.toggle_bookmark, name="toggle_bookmark"),
    path("materials/<int:post_id>/review/", views.submit_review, name="submit_review"),
    path("materials/<int:post_id>/report/", views.report_material, name="report_material"),

    path("viewer/<int:post_id>/", views.viewer, name="viewer"),
    path("pdf/<int:post_id>/file/", views.serve_pdf, name="serve_pdf"),

    path("library/", views.my_library, name="my_library"),
    path("teachers/<str:username>/", views.teacher_profile, name="teacher_profile"),
    path("teacher/dashboard/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/upload/", views.upload_post, name="upload_post"),
    path("teacher/materials/<int:post_id>/edit/", views.edit_post, name="edit_post"),

    path("staff/queue/", views.admin_queue, name="admin_queue"),
    path("staff/teachers/<int:profile_id>/approve/", views.admin_approve_teacher, name="admin_approve_teacher"),
    path("staff/teachers/<int:profile_id>/reject/", views.admin_reject_teacher, name="admin_reject_teacher"),
    path("staff/materials/<int:post_id>/approve/", views.admin_approve_post, name="admin_approve_post"),
    path("staff/materials/<int:post_id>/reject/", views.admin_reject_post, name="admin_reject_post"),
]
