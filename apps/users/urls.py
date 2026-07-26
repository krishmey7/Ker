from django.urls import path

from .views import OnboardingView, SignUpView, UserLoginView, UserLogoutView

app_name = "users"

urlpatterns = [
    path("onboarding/", OnboardingView.as_view(), name="onboarding"),
    path("onboarding/submit/", OnboardingView.as_view(), name="onboarding_submit"),
    path("signup/", SignUpView.as_view(), name="signup"),
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
]
