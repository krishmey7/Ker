"""Modèles jeu — questions, sessions, réponses, usage."""
from django.conf import settings
from django.db import models


class QuestionCategory(models.TextChoices):
    ROMANTIC = "romantic", "Romantique"
    FUNNY = "funny", "Drôle"
    SPICY = "spicy", "Spicy"
    DEEP = "deep", "Conversations profondes"
    KNOW_PARTNER = "know_partner", "Connaissance du partenaire"
    FUTURE = "future", "Futur du couple"
    HABITS = "habits", "Habitudes relationnelles"


class GameMode(models.TextChoices):
    SECRET_ANSWER = "secret_answer", "Réponse secrète"
    GUESS_PARTNER = "guess_partner", "Deviner le partenaire"
    TIMED = "timed", "Chronométré"
    CHALLENGE = "challenge", "Défi couple"
    COMPATIBILITY = "compatibility", "Compatibilité émotionnelle"


class SessionStatus(models.TextChoices):
    LOBBY = "lobby", "En attente"
    QUESTION = "question", "Question active"
    WAITING_REVEAL = "waiting_reveal", "En attente reveal"
    REVEAL = "reveal", "Révélation"
    FINISHED = "finished", "Terminée"


class Question(models.Model):
    """Question stockée en base (batch IA ou statique)."""

    text = models.TextField()
    category = models.CharField(max_length=32, choices=QuestionCategory.choices, db_index=True)
    spicy_level = models.PositiveSmallIntegerField(default=0)
    game_mode = models.CharField(max_length=32, choices=GameMode.choices, default=GameMode.SECRET_ANSWER)
    is_ai_generated = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "question"
        verbose_name_plural = "questions"
        ordering = ["-created_at"]

    def __str__(self):
        return self.text[:60]


class GameSession(models.Model):
    """Session de jeu liée à un couple."""

    couple = models.ForeignKey("couples.Couple", on_delete=models.CASCADE, related_name="sessions")
    current_question_index = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=24, choices=SessionStatus.choices, default=SessionStatus.LOBBY)
    current_question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    prefetched_question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Question pré-générée par Gemini pendant le reveal.",
    )
    game_mode = models.CharField(max_length=32, choices=GameMode.choices, default=GameMode.SECRET_ANSWER)
    category_filter = models.CharField(max_length=32, choices=QuestionCategory.choices, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "session de jeu"
        verbose_name_plural = "sessions de jeu"
        ordering = ["-started_at"]

    def __str__(self):
        return f"Session {self.pk} — {self.couple.room_code}"


class QuestionRound(models.Model):
    """Tour de jeu terminé — compatibilité calculée par l'IA pour une question."""

    couple = models.ForeignKey("couples.Couple", on_delete=models.CASCADE, related_name="question_rounds")
    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name="rounds")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="rounds")
    compatibility_percent = models.PositiveSmallIntegerField(default=50)
    compatibility_insight = models.CharField(max_length=300, blank=True)
    played_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("session", "question")]
        verbose_name = "tour de question"
        verbose_name_plural = "tours de questions"
        ordering = ["-played_at"]

    def __str__(self):
        return f"Round {self.pk} — {self.compatibility_percent}%"


class Answer(models.Model):
    """Réponse d'un partenaire à une question."""

    session = models.ForeignKey(GameSession, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="answers")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    guess_text = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reaction = models.CharField(max_length=32, blank=True)

    class Meta:
        unique_together = [("session", "question", "user")]
        verbose_name = "réponse"
        verbose_name_plural = "réponses"

    def __str__(self):
        return f"Réponse {self.user_id} — Q{self.question_id}"


class DailyUsage(models.Model):
    """Compteur quotidien de questions (freemium)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="daily_usages")
    date = models.DateField()
    questions_played = models.PositiveIntegerField(default=0)
    bonus_from_ads = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("user", "date")]
        verbose_name = "usage quotidien"
        verbose_name_plural = "usages quotidiens"


class Badge(models.Model):
    """Badge de gamification."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=64)
    emoji = models.CharField(max_length=8, default="🏆")
    description = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class CoupleBadge(models.Model):
    """Badge débloqué par un couple."""

    couple = models.ForeignKey("couples.Couple", on_delete=models.CASCADE, related_name="badges")
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("couple", "badge")]
