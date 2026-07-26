"""Modèles couple — room privée et gamification."""
import secrets
import string

from django.conf import settings
from django.db import models


def generate_room_code():
    """Génère un code room lisible (6 caractères)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(6))


class RelationshipDuration(models.TextChoices):
    LESS_THAN_1_YEAR = "less_than_1_year", "Moins d'un an"
    ONE_TO_THREE_YEARS = "1_to_3_years", "1 à 3 ans"
    MORE_THAN_3_YEARS = "more_than_3_years", "Plus de 3 ans"
    ENGAGED = "engaged", "Fiancés"


class ResidenceContinent(models.TextChoices):
    AFRICA = "africa", "Afrique"
    EUROPE = "europe", "Europe"
    NORTH_AMERICA = "north_america", "Amérique du Nord"
    SOUTH_AMERICA = "south_america", "Amérique du Sud"
    ASIA = "asia", "Asie"
    OCEANIA = "oceania", "Océanie"


class Couple(models.Model):
    """Lien entre deux partenaires."""

    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="couples_as_user1",
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="couples_as_user2",
    )
    room_code = models.CharField(max_length=8, unique=True, default=generate_room_code, db_index=True)
    level = models.PositiveIntegerField(default=1)
    compatibility_score = models.PositiveIntegerField(default=50)
    streak_days = models.PositiveIntegerField(default=0)
    last_played_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Profil couple pour adaptation IA
    relationship_duration = models.CharField(
        max_length=32,
        choices=RelationshipDuration.choices,
        default=RelationshipDuration.LESS_THAN_1_YEAR,
        verbose_name="Durée de la relation",
    )
    residence_continent = models.CharField(
        max_length=32,
        choices=ResidenceContinent.choices,
        default=ResidenceContinent.AFRICA,
        verbose_name="Continent de résidence",
    )
    is_long_distance = models.BooleanField(
        default=False,
        verbose_name="Relation à distance",
    )

    class Meta:
        verbose_name = "couple"
        verbose_name_plural = "couples"

    def __str__(self):
        return f"Couple {self.room_code}"

    @property
    def is_complete(self):
        """True si les deux partenaires sont connectés."""
        return self.user2_id is not None

    def partner_of(self, user):
        """Retourne le partenaire de l'utilisateur donné."""
        if self.user1_id == user.id:
            return self.user2
        if self.user2_id == user.id:
            return self.user1
        return None

    def contains(self, user):
        """Vérifie l'appartenance au couple."""
        return user.id in (self.user1_id, self.user2_id)
