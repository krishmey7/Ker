"""Vues paiement — orchestration uniquement, logique dans les services."""
import json
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from apps.couples.services import CoupleService
from apps.payments.models import PaymentStatus, PaymentTransaction, PlanType
from apps.payments.services import RewardedAdService, SubscriptionService, UsageLimitService
from apps.payments.services.kibawallet_service import KibaWalletError, KibaWalletService

logger = logging.getLogger(__name__)


class SubscriptionPlansView(LoginRequiredMixin, TemplateView):
    """Écran des deux offres : weekly + weekend."""

    template_name = "payments/premium.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        couple = CoupleService.get_active_couple(self.request.user)
        ctx["couple"] = couple
        ctx["usage_summary"] = UsageLimitService.get_usage_summary(self.request.user)
        if couple:
            ctx.update(SubscriptionService.get_monetization_context(couple))
        else:
            ctx["access"] = {}
        ctx["weekly_price"] = SubscriptionService.weekly_price()
        ctx["weekend_price"] = SubscriptionService.weekend_price()
        ctx["currency"] = getattr(settings, "PREMIUM_CURRENCY", "USD")
        ctx["is_weekend_window"] = SubscriptionService.is_weekend_window()
        ctx["kiba_configured"] = KibaWalletService.is_configured()
        return ctx


class PremiumView(SubscriptionPlansView):
    """Alias URL legacy."""

    pass


@login_required
@require_POST
def rewarded_ad_complete(request):
    """Valide une pub récompensée — backend uniquement."""
    couple = CoupleService.get_active_couple(request.user)
    if not couple or not couple.is_complete:
        return JsonResponse({"error": "Couple incomplet."}, status=400)

    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        body = {}

    ad_network = body.get("ad_network", "simulated")
    if not settings.DEBUG and ad_network == "simulated":
        ad_network = body.get("provider", "unknown")

    try:
        result = RewardedAdService.record_completion(request.user, couple, ad_network=ad_network)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(
        {
            "success": True,
            "unlocked": result.get("unlocked", False),
            "usage": result.get("usage"),
            "ad_reward": result.get("ad_reward"),
            "message": _ad_completion_message(result),
        }
    )


def _ad_completion_message(result: dict) -> str:
    if result.get("unlocked"):
        return f"❤️ Vous avez débloqué {RewardedAdService.extra_questions_per_unlock()} questions"
    if result.get("ad_reward", {}).get("waiting_for_partner"):
        return "En attente du partenaire ❤️"
    return "Pub terminée ❤️"


@login_required
def rewarded_ad_status(request):
    couple = CoupleService.get_active_couple(request.user)
    if not couple:
        return JsonResponse({"error": "Pas de couple."}, status=400)
    return JsonResponse(
        {
            "usage": UsageLimitService.get_usage_summary(request.user),
            "ad_reward": RewardedAdService.get_status(couple, request.user.id),
            "access": SubscriptionService.can_access_questions(couple),
        }
    )


@login_required
@require_POST
@csrf_exempt
def activate_weekly_stub(request):
    """Stub dev — active le premium hebdomadaire (1,99$/semaine)."""
    if not settings.DEBUG:
        return JsonResponse({"error": "Endpoint non disponible en production"}, status=403)
    couple = CoupleService.get_active_couple(request.user)
    if not couple:
        return JsonResponse({"error": "Pas de couple actif"}, status=400)
    try:
        SubscriptionService.activate_weekly(couple, request.user, external_id="stub_weekly")
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(
        {
            "status": "weekly",
            "usage": UsageLimitService.get_usage_summary(request.user),
            "access": SubscriptionService.can_access_questions(couple),
            "message": "Illimité ❤️ — Premium hebdomadaire activé",
        }
    )


@login_required
@require_POST
@csrf_exempt
def activate_weekend_stub(request):
    """Stub dev — active le pass weekend (0,50$)."""
    if not settings.DEBUG:
        return JsonResponse({"error": "Endpoint non disponible en production"}, status=403)
    couple = CoupleService.get_active_couple(request.user)
    if not couple:
        return JsonResponse({"error": "Pas de couple actif"}, status=400)
    try:
        SubscriptionService.activate_weekend(couple, request.user, external_id="stub_weekend")
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    access = SubscriptionService.can_access_questions(couple)
    return JsonResponse(
        {
            "status": "weekend",
            "usage": UsageLimitService.get_usage_summary(request.user),
            "access": access,
            "message": access.get("badge") or "Pass weekend activé 🔥",
        }
    )


@login_required
@require_POST
def activate_premium_stub(request):
    """Rétrocompatibilité — redirige vers weekly."""
    return activate_weekly_stub(request)


@login_required
@require_POST
def kiba_create_payment(request):
    """Lance un paiement Mobile Money (USSD) via KibaWallet."""
    couple = CoupleService.get_active_couple(request.user)
    if not couple or not couple.is_complete:
        return JsonResponse({"error": "Couple incomplet."}, status=400)

    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        body = {}

    plan = body.get("plan_type", PlanType.WEEKLY)
    if plan not in (PlanType.WEEKLY, PlanType.WEEKEND):
        return JsonResponse({"error": "Plan invalide."}, status=400)

    mobile = body.get("mobile_number", "").strip()
    if not mobile:
        return JsonResponse({"error": "Numéro Mobile Money requis (+243…)."}, status=400)

    try:
        txn = KibaWalletService.create_couple_payment(
            couple, request.user, plan, mobile, currency=body.get("currency")
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except KibaWalletError as exc:
        return JsonResponse({"error": str(exc)}, status=502)

    return JsonResponse(
        {
            "transaction_id": txn.pk,
            "external_reference": txn.external_reference,
            "kiba_id": txn.external_id,
            "status": txn.kiba_status or "PENDING",
            "message": "Validez le paiement USSD sur votre téléphone.",
            "poll_url": f"/payments/api/kiba/status/{txn.pk}/",
        }
    )


@login_required
@require_GET
def kiba_payment_status(request, transaction_id: int):
    """Polling statut paiement KibaWallet."""
    couple = CoupleService.get_active_couple(request.user)
    if not couple:
        return JsonResponse({"error": "Pas de couple."}, status=400)

    try:
        txn = PaymentTransaction.objects.get(pk=transaction_id, couple=couple)
    except PaymentTransaction.DoesNotExist:
        return JsonResponse({"error": "Transaction introuvable."}, status=404)

    if txn.status == PaymentStatus.COMPLETED:
        return JsonResponse(
            {
                "status": "COMPLETED",
                "message": "Paiement confirmé ❤️",
                "usage": UsageLimitService.get_usage_summary(request.user),
                "access": SubscriptionService.can_access_questions(couple),
            }
        )
    if txn.status == PaymentStatus.FAILED:
        return JsonResponse({"status": "FAILED", "message": "Paiement refusé ou annulé."})

    try:
        data = KibaWalletService.fetch_payment_status(txn)
    except KibaWalletError as exc:
        return JsonResponse({"status": txn.kiba_status or "PENDING", "error": str(exc)})

    txn.refresh_from_db()
    if txn.status == PaymentStatus.COMPLETED:
        return JsonResponse(
            {
                "status": "SUCCEEDED",
                "message": "Paiement confirmé ❤️",
                "usage": UsageLimitService.get_usage_summary(request.user),
                "access": SubscriptionService.can_access_questions(couple),
            }
        )
    return JsonResponse(
        {
            "status": data.get("status", txn.kiba_status or "PENDING"),
            "message": "En attente de validation USSD sur votre téléphone…",
        }
    )


@csrf_exempt
@require_POST
def kibawallet_webhook(request):
    """Webhook KibaWallet — corps brut pour vérification HMAC."""
    raw = request.body
    sig = request.headers.get("X-Kiba-Signature") or request.META.get("HTTP_X_KIBA_SIGNATURE")
    if not KibaWalletService.verify_webhook_signature(raw, sig):
        logger.warning("Kiba webhook: signature invalide")
        return JsonResponse({"error": "invalid signature"}, status=401)

    try:
        event = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid json"}, status=400)

    try:
        KibaWalletService.handle_webhook_event(event)
    except Exception:
        logger.exception("Kiba webhook processing failed")
        return JsonResponse({"error": "processing failed"}, status=500)

    return JsonResponse({"ok": True})


@login_required
@require_POST
def watch_ad_reward(request):
    return rewarded_ad_complete(request)
