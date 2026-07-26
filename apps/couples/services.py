"""Services couple — logique métier hors views."""
from django.db import transaction
from django.utils import timezone

from apps.couples.models import Couple
from apps.users.models import User


class CoupleService:
    """Création, jonction et stats couple."""

    @staticmethod
    @transaction.atomic
    def create_room(
        user: User,
        relationship_duration: str = "less_than_1_year",
        residence_continent: str = "africa",
        is_long_distance: bool = False,
    ) -> Couple:
        """Crée une room et assigne user1 avec le profil du couple."""
        existing = Couple.objects.filter(user1=user, user2__isnull=True).first()
        if existing:
            return existing
        return Couple.objects.create(
            user1=user,
            relationship_duration=relationship_duration,
            residence_continent=residence_continent,
            is_long_distance=is_long_distance,
        )

    @staticmethod
    @transaction.atomic
    def join_room(
        user: User,
        room_code: str,
        relationship_duration: str | None = None,
        residence_continent: str | None = None,
        is_long_distance: bool | None = None,
    ) -> Couple:
        """Rejoint une room via code avec mise à jour optionnelle du profil."""
        code = room_code.strip().upper()
        couple = Couple.objects.select_for_update().filter(room_code=code).first()
        if not couple:
            raise ValueError("Code invalide.")
        if couple.user2_id:
            if couple.contains(user):
                return couple
            raise ValueError("Cette room est déjà complète.")
        if couple.user1_id == user.id:
            raise ValueError("Vous ne pouvez pas rejoindre votre propre room.")
        couple.user2 = user
        
        # Mettre à jour le profil si fourni par user2
        if relationship_duration is not None:
            couple.relationship_duration = relationship_duration
        if residence_continent is not None:
            couple.residence_continent = residence_continent
        if is_long_distance is not None:
            couple.is_long_distance = is_long_distance
            
        couple.save(update_fields=["user2", "relationship_duration", "residence_continent", "is_long_distance"])
        return couple

    @staticmethod
    def get_active_couple(user: User) -> Couple | None:
        """Couple actif de l'utilisateur."""
        return (
            Couple.objects.filter(user1=user)
            .exclude(user2__isnull=True)
            .first()
            or Couple.objects.filter(user2=user).first()
        )

    @staticmethod
    def get_pending_couple(user: User) -> Couple | None:
        """Room en attente du partenaire."""
        return Couple.objects.filter(user1=user, user2__isnull=True).first()

    @staticmethod
    @transaction.atomic
    def update_streak(couple: Couple) -> int:
        """Met à jour le streak quotidien."""
        today = timezone.localdate()
        if couple.last_played_at == today:
            return couple.streak_days
        if couple.last_played_at and (today - couple.last_played_at).days == 1:
            couple.streak_days += 1
        else:
            couple.streak_days = 1
        couple.last_played_at = today
        couple.save(update_fields=["streak_days", "last_played_at"])
        return couple.streak_days
