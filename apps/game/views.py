"""Vues jeu — pages UX de la boucle produit."""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.couples.services import CoupleService
from apps.game.models import GameSession
from apps.game.services import (
    CompatibilityService,
    CoupleActivityService,
    CoupleProgressService,
)
from apps.payments.services import UsageLimitService


class WelcomeView(TemplateView):
    template_name = "core/welcome.html"


@login_required
def play_session(request, session_id=None):
    """Écran de jeu temps réel."""
    couple = CoupleService.get_active_couple(request.user)
    if not couple or not couple.is_complete:
        return redirect("couples:setup")
    return redirect("game:session", room_code=couple.room_code)


class GameSessionView(LoginRequiredMixin, TemplateView):
    """Session live — WebSocket + Alpine."""

    template_name = "game/session.html"

    def dispatch(self, request, *args, **kwargs):
        couple = CoupleService.get_active_couple(request.user)
        if not couple or couple.room_code != kwargs["room_code"].upper():
            return redirect("couples:setup")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from django.conf import settings

        ctx = super().get_context_data(**kwargs)
        ctx["room_code"] = kwargs["room_code"].upper()
        couple = CoupleService.get_active_couple(self.request.user)
        ctx["couple"] = couple
        if couple:
            ctx["couple_stats"] = CoupleProgressService.get_stats(couple)
            ctx["usage_summary"] = UsageLimitService.get_usage_summary_for_couple(couple)
        ctx["ker_ad_debug"] = settings.DEBUG
        ctx["ker_ad_simulation_seconds"] = getattr(settings, "REWARDED_AD_SIMULATION_SECONDS", 30)
        return ctx


class HistoryView(LoginRequiredMixin, TemplateView):
    """Historique des questions répondues à deux."""

    template_name = "game/history.html"

    def dispatch(self, request, *args, **kwargs):
        couple = CoupleService.get_active_couple(request.user)
        if not couple or not couple.is_complete:
            return redirect("couples:setup")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        couple = CoupleService.get_active_couple(self.request.user)
        ctx["couple"] = couple
        ctx["history"] = CompatibilityService.get_history_for_couple(couple)
        ctx["couple_stats"] = CoupleProgressService.get_stats(couple)
        return ctx


class LevelActivityView(LoginRequiredMixin, TemplateView):
    """Activité de couple suggérée par Gemini selon le niveau et la compatibilité."""

    template_name = "game/level_activity.html"

    def dispatch(self, request, *args, **kwargs):
        couple = CoupleService.get_active_couple(request.user)
        if not couple or not couple.is_complete:
            return redirect("couples:setup")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        couple = CoupleService.get_active_couple(self.request.user)
        ctx["couple"] = couple
        ctx["couple_stats"] = CoupleProgressService.get_stats(couple)
        ctx["activity"] = CoupleActivityService.suggest_activity(couple)
        return ctx


class StatsView(LoginRequiredMixin, TemplateView):
    template_name = "game/stats.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        couple = CoupleService.get_active_couple(self.request.user)
        ctx["couple"] = couple
        if couple:
            ctx["sessions"] = GameSession.objects.filter(couple=couple).order_by("-started_at")[:10]
            ctx["badges"] = couple.badges.select_related("badge")
            ctx["couple_stats"] = CoupleProgressService.get_stats(couple)
            ctx["usage_summary"] = UsageLimitService.get_usage_summary_for_couple(couple)
        return ctx


class PaywallView(LoginRequiredMixin, TemplateView):
    template_name = "game/paywall.html"

    def get_context_data(self, **kwargs):
        from django.conf import settings

        ctx = super().get_context_data(**kwargs)
        couple = CoupleService.get_active_couple(self.request.user)
        ctx["couple"] = couple
        if couple:
            ctx["usage_summary"] = UsageLimitService.get_usage_summary_for_couple(couple)
        ctx["premium_monthly_price"] = settings.PREMIUM_MONTHLY_PRICE
        ctx["free_daily_questions"] = settings.FREE_DAILY_QUESTIONS
        return ctx
