from django.urls import path

from .views import (
    GameSessionView,
    HistoryView,
    LevelActivityView,
    PaywallView,
    StatsView,
    play_session,
)

app_name = "game"

urlpatterns = [
    path("play/", play_session, name="play"),
    path("session/<str:room_code>/", GameSessionView.as_view(), name="session"),
    path("history/", HistoryView.as_view(), name="history"),
    path("level-activity/", LevelActivityView.as_view(), name="level_activity"),
    path("stats/", StatsView.as_view(), name="stats"),
    path("paywall/", PaywallView.as_view(), name="paywall"),
]
