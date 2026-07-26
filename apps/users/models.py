"""Modèle utilisateur personnalisé."""
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Utilisateur de l'application couple."""

    display_name = models.CharField(max_length=80, blank=True)
    avatar_emoji = models.CharField(max_length=8, default="💑")
    email = models.EmailField(blank=True, null=True)  # Email optionnel, utilise phone_number à la place

    class Meta:
        verbose_name = "utilisateur"
        verbose_name_plural = "utilisateurs"

    def __str__(self):
        return self.display_name or self.username

    @property
    def label(self):
        """Libellé affiché dans l'UI."""
        return self.display_name or self.get_full_name() or self.username
