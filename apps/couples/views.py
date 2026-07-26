"""Vues couple — orchestration uniquement."""
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.couples.services import CoupleService


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "couples/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ctx["couple"] = CoupleService.get_active_couple(user)
        ctx["pending"] = CoupleService.get_pending_couple(user)
        return ctx


@login_required
def create_room(request):
    """Crée une room privée avec le profil du couple."""
    relationship_duration = request.POST.get("relationship_duration", "less_than_1_year")
    residence_continent = request.POST.get("residence_continent", "africa")
    is_long_distance = request.POST.get("is_long_distance") == "on"
    
    couple = CoupleService.create_room(
        request.user,
        relationship_duration=relationship_duration,
        residence_continent=residence_continent,
        is_long_distance=is_long_distance,
    )
    return redirect("couples:waiting", code=couple.room_code)


@login_required
def join_room(request):
    """Rejoint une room via formulaire POST avec profil optionnel."""
    code = request.POST.get("room_code", "")
    
    # Profil optionnel pour user2
    relationship_duration = request.POST.get("relationship_duration") or None
    residence_continent = request.POST.get("residence_continent") or None
    is_long_distance = request.POST.get("is_long_distance") == "on" if request.POST.get("is_long_distance") else None
    
    try:
        couple = CoupleService.join_room(
            request.user,
            code,
            relationship_duration=relationship_duration,
            residence_continent=residence_continent,
            is_long_distance=is_long_distance,
        )
    except ValueError as exc:
        return render(
            request,
            "couples/join.html",
            {"error": str(exc)},
            status=400,
        )
    if couple.is_complete:
        return redirect("couples:dashboard")
    return redirect("couples:waiting", code=couple.room_code)


class JoinFormView(LoginRequiredMixin, TemplateView):
    template_name = "couples/join.html"


class WaitingView(LoginRequiredMixin, TemplateView):
    template_name = "couples/waiting.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        code = self.kwargs["code"]
        ctx["room_code"] = code
        ctx["couple"] = CoupleService.get_pending_couple(self.request.user) or CoupleService.get_active_couple(
            self.request.user
        )
        return ctx


class SetupView(LoginRequiredMixin, View):
    """Écran créer / rejoindre."""

    def get(self, request):
        if CoupleService.get_active_couple(request.user):
            return redirect("couples:dashboard")
        return render(request, "couples/setup.html")
