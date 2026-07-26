from django.contrib import admin

from .models import AdReward, CoupleDailyUsage, PaymentTransaction, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("couple", "plan_type", "is_active", "start_date", "end_date", "auto_renew")
    list_filter = ("plan_type", "is_active")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("couple", "user", "plan_type", "amount", "currency", "status", "created_at")
    list_filter = ("plan_type", "status")


@admin.register(CoupleDailyUsage)
class CoupleDailyUsageAdmin(admin.ModelAdmin):
    list_display = ("couple", "date", "questions_played", "extra_questions")
    list_filter = ("date",)


@admin.register(AdReward)
class AdRewardAdmin(admin.ModelAdmin):
    list_display = ("couple", "user", "completed", "credits_applied", "reward_type", "created_at")
    list_filter = ("completed", "credits_applied", "reward_type")
