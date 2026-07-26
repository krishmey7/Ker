from django.urls import path

from .views import DashboardView, JoinFormView, SetupView, WaitingView, create_room, join_room, waiting_status

app_name = "couples"

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("setup/", SetupView.as_view(), name="setup"),
    path("create/", create_room, name="create"),
    path("join/", JoinFormView.as_view(), name="join"),
    path("join/submit/", join_room, name="join_submit"),
    path("waiting/<str:code>/status/", waiting_status, name="waiting_status"),
    path("waiting/<str:code>/", WaitingView.as_view(), name="waiting"),
]
