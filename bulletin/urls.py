from django.urls import path
from . import views

app_name = "bulletin"

urlpatterns = [
    path("", views.bulletin_home, name="home"),
    path("<int:pk>/", views.bulletin_detail, name="detail"),
    path("create/", views.bulletin_create, name="create"),
]
