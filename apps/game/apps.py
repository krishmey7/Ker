from django.apps import AppConfig


class GameConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.game"
    label = "game"

    def ready(self):
        from apps.game.db_utils import setup_sqlite_wal

        setup_sqlite_wal()
