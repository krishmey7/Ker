"""
Client API KibaWallet — Mobile Money (USSD) RDC, USD/CDF.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from decimal import Decimal
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.couples.models import Couple
from apps.payments.models import PaymentStatus, PaymentTransaction, PlanType
from apps.payments.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)


class KibaWalletError(Exception):
    """Erreur appel API KibaWallet."""


class KibaWalletService:
    """Encaissement Mobile Money via KibaWallet."""

    @staticmethod
    def is_configured() -> bool:
        return bool(settings.KIBA_PUBLIC_KEY and settings.KIBA_SECRET_KEY)

    @staticmethod
    def _headers() -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-Kiba-Public-Key": settings.KIBA_PUBLIC_KEY,
            "Authorization": f"Bearer {settings.KIBA_SECRET_KEY}",
        }
        # Log avec masquage des secrets
        logger.debug(
            "KibaWallet headers: X-Kiba-Public-Key=%s…, Authorization=Bearer %s…",
            settings.KIBA_PUBLIC_KEY[:20] if settings.KIBA_PUBLIC_KEY else "MISSING",
            settings.KIBA_SECRET_KEY[:20] if settings.KIBA_SECRET_KEY else "MISSING",
        )
        return headers

    @staticmethod
    def _request(method: str, path: str, body: dict | None = None) -> dict[str, Any]:
        base = settings.KIBA_API_BASE_URL.rstrip("/")
        url = f"{base}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = Request(url, data=data, method=method, headers=KibaWalletService._headers())
        try:
            with urlopen(req, timeout=settings.KIBA_REQUEST_TIMEOUT) as resp:
                payload = resp.read().decode("utf-8")
                return json.loads(payload) if payload else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            logger.warning("KibaWallet HTTP %s: %s", exc.code, detail[:500])
            raise KibaWalletError(detail or f"HTTP {exc.code}") from exc
        except URLError as exc:
            raise KibaWalletError(str(exc)) from exc

    @staticmethod
    def sanitize_description(text: str) -> str:
        """Nettoie la description pour Kelpay — ASCII seulement."""
        if not text:
            return "Payment"
        
        # Remplacer les caractères spéciaux UTF-8 par des équivalents ASCII
        replacements = {
            "—": "-",      # Em-dash → tiret
            "–": "-",      # En-dash → tiret
            "'": "'",      # Apostrophe courbe → apostrophe simple
            "'": "'",      # Apostrophe courbe alternative
            """: '"',      # Guillemet courbe → guillemet droit
            """: '"',      # Guillemet courbe
            "«": '"',      # Guillemet français
            "»": '"',      # Guillemet français
            "é": "e",      # Accents français
            "è": "e",
            "ê": "e",
            "à": "a",
            "ç": "c",
            "ô": "o",
            "û": "u",
        }
        
        result = text
        for utf8_char, ascii_char in replacements.items():
            result = result.replace(utf8_char, ascii_char)
        
        # Garder seulement ASCII + espaces
        result = "".join(c for c in result if ord(c) < 128)
        
        # Limiter à 100 caractères (requête Kelpay)
        result = result[:100].strip()
        
        logger.debug("sanitize_description: %s → %s", repr(text), repr(result))
        return result or "Payment"

    @staticmethod
    def normalize_phone(raw: str) -> str:
        """Format international +243…"""
        if not raw:
            raise ValueError("Numéro vide.")
        
        # Enlever espaces, tirets, points
        digits = "".join(c for c in raw if c.isdigit())
        if not digits:
            raise ValueError(f"Aucun chiffre trouvé dans : {raw}")
        
        logger.debug("normalize_phone: raw=%s, digits=%s", raw, digits)
        
        # Cas 1: déjà +243...
        if raw.strip().startswith("+243"):
            result = raw.strip()
            logger.debug("→ +243 prefix: %s", result)
            return result
        
        # Cas 2: 243... (sans +)
        if digits.startswith("243"):
            result = f"+{digits}"
            logger.debug("→ Add +: %s", result)
            return result
        
        # Cas 3: 0900... → +243900...
        if digits.startswith("0"):
            result = f"+243{digits[1:]}"
            logger.debug("→ Replace 0: %s", result)
            return result
        
        # Cas 4: juste 9 chiffres → ajouter +243
        if len(digits) == 9:
            result = f"+243{digits}"
            logger.debug("→ Add +243: %s", result)
            return result
        
        # Erreur
        raise ValueError(f"Format invalide : {raw} (chiffres: {digits})")

    @staticmethod
    def create_couple_payment(
        couple: Couple,
        user,
        plan_type: str,
        mobile_number: str,
        *,
        currency: str | None = None,
    ) -> PaymentTransaction:
        """Crée une transaction locale PENDING et lance l'USSD via KibaWallet."""
        if not KibaWalletService.is_configured():
            raise KibaWalletError("KibaWallet n'est pas configuré (clés API manquantes).")

        if plan_type == PlanType.WEEKLY:
            amount = SubscriptionService.weekly_price()
            description = "Ker - Premium weekly couple"
        elif plan_type == PlanType.WEEKEND:
            amount = SubscriptionService.weekend_price()
            description = "Ker - Weekend pass couple"
        else:
            raise ValueError("Plan non pris en charge.")

        phone = KibaWalletService.normalize_phone(mobile_number)
        currency = (currency or getattr(settings, "PREMIUM_CURRENCY", "USD")).upper()
        external_reference = f"ker-{couple.pk}-{uuid.uuid4().hex[:12]}"

        txn = PaymentTransaction.objects.create(
            couple=couple,
            user=user,
            plan_type=plan_type,
            status=PaymentStatus.PENDING,
            amount=amount,
            currency=currency,
            external_reference=external_reference,
            provider="kibawallet",
            mobile_number=phone,
        )

        payload = {
            "mobilenumber": phone,
            "amount": float(amount),
            "currency": currency,
            "external_reference": external_reference,
            "description": KibaWalletService.sanitize_description(description),
        }
        logger.info("KibaWallet API request: %s", json.dumps(payload, default=str))
        
        try:
            response = KibaWalletService._request(
                "POST",
                "/v1/payments",
                payload,
            )
            logger.info("KibaWallet API response: %s", json.dumps(response, default=str))
        except KibaWalletError as exc:
            logger.error("KibaWallet API error: %s", str(exc))
            txn.status = PaymentStatus.FAILED
            txn.save(update_fields=["status"])
            raise

        txn.external_id = str(response.get("id") or response.get("transaction_id") or "")
        txn.kiba_status = str(response.get("status") or "PENDING")
        txn.save(update_fields=["external_id", "kiba_status"])

        return txn

    @staticmethod
    def fetch_payment_status(txn: PaymentTransaction) -> dict[str, Any]:
        """Interroge GET /v1/payments/{id}."""
        if not txn.external_id:
            raise KibaWalletError("Transaction Kiba sans identifiant.")
        data = KibaWalletService._request("GET", f"/v1/payments/{txn.external_id}")
        status = str(data.get("status") or "").upper()
        if status:
            txn.kiba_status = status
            txn.save(update_fields=["kiba_status"])
        if status == "SUCCEEDED":
            KibaWalletService.fulfill_transaction(txn.external_reference, kiba_payload=data)
        elif status == "FAILED":
            PaymentTransaction.objects.filter(pk=txn.pk).update(status=PaymentStatus.FAILED)
        return data

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
        secret = getattr(settings, "KIBA_WEBHOOK_SECRET", "") or ""
        if not secret or not signature_header:
            return False
        expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        try:
            return hmac.compare_digest(expected, signature_header.strip())
        except ValueError:
            return False

    @staticmethod
    @transaction.atomic
    def fulfill_transaction(
        external_reference: str,
        *,
        kiba_payload: dict | None = None,
    ) -> PaymentTransaction | None:
        """Active l'abonnement une seule fois (idempotent)."""
        txn = (
            PaymentTransaction.objects.select_for_update()
            .filter(external_reference=external_reference)
            .first()
        )
        if not txn:
            logger.warning("Kiba fulfill: référence inconnue %s", external_reference)
            return None
        if txn.status == PaymentStatus.COMPLETED:
            return txn

        txn.status = PaymentStatus.COMPLETED
        txn.completed_at = timezone.now()
        if kiba_payload:
            txn.kiba_status = "SUCCEEDED"
            txn.kiba_reference = str(
                kiba_payload.get("kelpay_reference") or txn.kiba_reference or ""
            )[:128]
        txn.save(
            update_fields=["status", "completed_at", "kiba_status", "kiba_reference"]
        )

        user = txn.user or txn.couple.user1
        if txn.plan_type == PlanType.WEEKLY:
            SubscriptionService._apply_weekly_plan(txn.couple, user, external_id=txn.external_reference)
        elif txn.plan_type == PlanType.WEEKEND:
            SubscriptionService._apply_weekend_plan(txn.couple, user, external_id=txn.external_reference)

        logger.info("Kiba payment fulfilled ref=%s plan=%s", external_reference, txn.plan_type)
        return txn

    @staticmethod
    def handle_webhook_event(event: dict) -> None:
        """Traite payment.success / payment.failed."""
        name = event.get("event", "")
        data = event.get("data") or {}
        ref = data.get("external_reference", "")
        if not ref:
            return
        if name == "payment.success":
            KibaWalletService.fulfill_transaction(ref, kiba_payload=data)
        elif name == "payment.failed":
            PaymentTransaction.objects.filter(external_reference=ref).exclude(
                status=PaymentStatus.COMPLETED
            ).update(status=PaymentStatus.FAILED, kiba_status="FAILED")
