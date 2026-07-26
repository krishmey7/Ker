"""Monétisation — abonnements, quota, pubs récompensées et paiements."""
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PlanType(models.TextChoices):
    """Type de plan couple."""

    NONE = "none", "Gratuit"
    WEEKLY = "weekly", "Premium hebdomadaire"
    WEEKEND = "weekend", "Pass weekend"


class SubscriptionStatus(models.TextChoices):
    """Rétrocompatibilité — préférer PlanType."""

    FREE = "free", "Gratuit"
    PREMIUM = "premium", "Premium Couple"
    EXPIRED = "expired", "Expiré"


class PaymentStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    COMPLETED = "completed", "Complété"
    FAILED = "failed", "Échoué"
    REFUNDED = "refunded", "Remboursé"


class PaymentProvider(models.TextChoices):
    STUB = "stub", "Stub (dev)"
    KIBAWALLET = "kibawallet", "KibaWallet"


class Subscription(models.Model):
    """Abonnement partagé par le couple (1 paiement = 2 utilisateurs)."""

    couple = models.OneToOneField("couples.Couple", on_delete=models.CASCADE, related_name="subscription")
    plan_type = models.CharField(
        max_length=16,
        choices=PlanType.choices,
        default=PlanType.NONE,
        db_index=True,
    )
    is_active = models.BooleanField(default=False)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    auto_renew = models.BooleanField(default=False)
    external_id = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Champs legacy — conservés pour migrations existantes
    status = models.CharField(
        max_length=16,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.FREE,
        blank=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "abonnement couple"
        verbose_name_plural = "abonnements couple"

    def __str__(self):
        return f"Couple {self.couple_id} — {self.plan_type} ({'actif' if self.is_active else 'inactif'})"

    @property
    def is_premium(self) -> bool:
        """Rétrocompat — True si premium hebdomadaire actif."""
        if self.end_date and self.end_date < timezone.now():
            return False
        return self.is_active and self.plan_type == PlanType.WEEKLY


class PaymentTransaction(models.Model):
    """Trace des achats (stub local ou passerelle future)."""

    couple = models.ForeignKey("couples.Couple", on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
    )
    plan_type = models.CharField(max_length=16, choices=PlanType.choices)
    status = models.CharField(
        max_length=16,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
    )
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    currency = models.CharField(max_length=8, default="USD")
    provider = models.CharField(
        max_length=24,
        choices=PaymentProvider.choices,
        default=PaymentProvider.STUB,
        db_index=True,
    )
    external_reference = models.CharField(max_length=64, unique=True, db_index=True)
    external_id = models.CharField(max_length=128, blank=True, help_text="ID transaction KibaWallet")
    mobile_number = models.CharField(max_length=24, blank=True)
    kiba_status = models.CharField(max_length=24, blank=True)
    kiba_reference = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "transaction"
        verbose_name_plural = "transactions"

    def __str__(self):
        return f"{self.plan_type} — {self.amount} {self.currency} ({self.status})"


class CoupleDailyUsage(models.Model):
    """Quota quotidien partagé par le couple."""

    couple = models.ForeignKey("couples.Couple", on_delete=models.CASCADE, related_name="daily_usages")
    date = models.DateField()
    questions_played = models.PositiveIntegerField(default=0)
    extra_questions = models.PositiveIntegerField(
        default=0,
        help_text="Questions bonus débloquées via pubs récompensées.",
    )

    class Meta:
        unique_together = [("couple", "date")]
        verbose_name = "usage quotidien couple"
        verbose_name_plural = "usages quotidiens couple"

    def __str__(self):
        return f"Couple {self.couple_id} — {self.date} ({self.questions_played}+{self.extra_questions})"


class RewardType(models.TextChoices):
    REWARDED_VIDEO = "rewarded_video", "Vidéo récompensée"


class AdReward(models.Model):
    """Validation pub récompensée par utilisateur (cycle couple à deux)."""

    couple = models.ForeignKey("couples.Couple", on_delete=models.CASCADE, related_name="ad_rewards")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ad_rewards",
    )
    reward_cycle_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    completed = models.BooleanField(default=False)
    reward_type = models.CharField(
        max_length=32,
        choices=RewardType.choices,
        default=RewardType.REWARDED_VIDEO,
    )
    credits_applied = models.BooleanField(
        default=False,
        help_text="True lorsque le couple a reçu les questions bonus.",
    )
    ad_network = models.CharField(max_length=32, default="simulated")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = [("reward_cycle_id", "user")]
        verbose_name = "récompense pub"
        verbose_name_plural = "récompenses pub"

    def __str__(self):
        return f"AdReward {self.user_id} — cycle {self.reward_cycle_id}"
