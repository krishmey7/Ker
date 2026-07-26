# Migration — quota partagé par couple
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("couples", "0002_initial"),
        ("payments", "0002_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CoupleDailyUsage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("date", models.DateField()),
                ("questions_played", models.PositiveIntegerField(default=0)),
                (
                    "couple",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="daily_usages",
                        to="couples.couple",
                    ),
                ),
            ],
            options={
                "verbose_name": "usage quotidien couple",
                "verbose_name_plural": "usages quotidiens couple",
                "unique_together": {("couple", "date")},
            },
        ),
        migrations.AddField(
            model_name="adreward",
            name="couple",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ad_rewards",
                to="couples.couple",
            ),
        ),
        migrations.AddField(
            model_name="adreward",
            name="granted_by",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="ad_rewards_granted",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RemoveField(
            model_name="adreward",
            name="user",
        ),
        migrations.RemoveField(
            model_name="adreward",
            name="questions_granted",
        ),
        migrations.AlterField(
            model_name="adreward",
            name="couple",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ad_rewards",
                to="couples.couple",
            ),
        ),
    ]
