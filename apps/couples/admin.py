from django.contrib import admin

from .models import Couple


@admin.register(Couple)
class CoupleAdmin(admin.ModelAdmin):
    list_display = ("room_code", "user1", "user2", "level", "streak_days", "compatibility_score")
    search_fields = ("room_code",)
