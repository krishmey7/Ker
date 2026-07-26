from django.urls import path

from .views import WelcomeView

app_name = "core"

urlpatterns = [
    path("", WelcomeView.as_view(), name="welcome"),
]
