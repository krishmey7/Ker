from django.contrib import admin, messages
from django.db.models import Count

from .models import Answer, Badge, CoupleBadge, DailyUsage, GameSession, Question, QuestionRound


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = (
        "text_short",
        "category",
        "spicy_level",
        "is_ai_generated",
        "is_active",
        "created_at",
    )
    list_filter = ("category", "is_active", "is_ai_generated", "spicy_level")
    search_fields = ("text",)
    list_per_page = 50
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    actions = ["activate_questions", "deactivate_questions", "mark_as_bank", "mark_as_ai"]

    fieldsets = (
        (None, {"fields": ("text", "category", "spicy_level", "game_mode")}),
        (
            "Publication",
            {
                "fields": ("is_active", "is_ai_generated"),
                "description": (
                    "Banque fallback : is_ai_generated=False (1000 questions seed). "
                    "Jamais re-proposée au même couple via le moteur d'usage."
                ),
            },
        ),
        ("Meta", {"fields": ("created_at",)}),
    )

    @admin.display(description="Question")
    def text_short(self, obj):
        return obj.text[:80] + ("…" if len(obj.text) > 80 else "")

    @admin.action(description="Activer la sélection")
    def activate_questions(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} question(s) activée(s).", messages.SUCCESS)

    @admin.action(description="Désactiver la sélection")
    def deactivate_questions(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} question(s) désactivée(s).", messages.WARNING)

    @admin.action(description="Marquer comme banque (fallback)")
    def mark_as_bank(self, request, queryset):
        n = queryset.update(is_ai_generated=False)
        self.message_user(request, f"{n} question(s) en banque statique.", messages.SUCCESS)

    @admin.action(description="Marquer comme générée IA")
    def mark_as_ai(self, request, queryset):
        n = queryset.update(is_ai_generated=True)
        self.message_user(request, f"{n} question(s) marquées IA.", messages.SUCCESS)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        stats = (
            Question.objects.values("category", "is_ai_generated", "is_active")
            .annotate(c=Count("id"))
            .order_by("category")
        )
        extra_context["question_stats"] = list(stats)
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(GameSession)
class GameSessionAdmin(admin.ModelAdmin):
    list_display = ("couple", "status", "current_question_index", "started_at")
    list_filter = ("status",)


@admin.register(QuestionRound)
class QuestionRoundAdmin(admin.ModelAdmin):
    list_display = ("couple", "question", "compatibility_percent", "played_at")
    list_filter = ("played_at",)


admin.site.register(Answer)
admin.site.register(DailyUsage)
admin.site.register(Badge)
admin.site.register(CoupleBadge)
