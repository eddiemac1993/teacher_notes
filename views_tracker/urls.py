from django.urls import path
from . import views

app_name = "views_tracker"

urlpatterns = [
    path("start/", views.start, name="start"),
    path("interact/", views.interact, name="interact"),
    path("heartbeat/", views.heartbeat, name="heartbeat"),
]
