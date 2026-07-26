from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("couples", "0001_initial"),
        ("game", "0004_gamesession_prefetched_question"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionRound",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("compatibility_percent", models.PositiveSmallIntegerField(default=50)),
                ("compatibility_insight", models.CharField(blank=True, max_length=300)),
                ("played_at", models.DateTimeField(auto_now_add=True)),
                (
                    "couple",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="question_rounds",
                        to="couples.couple",
                    ),
                ),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rounds",
                        to="game.question",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="rounds",
                        to="game.gamesession",
                    ),
                ),
            ],
            options={
                "verbose_name": "tour de question",
                "verbose_name_plural": "tours de questions",
                "ordering": ["-played_at"],
                "unique_together": {("session", "question")},
            },
        ),
    ]
