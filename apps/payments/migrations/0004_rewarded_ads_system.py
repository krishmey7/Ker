# Migration — système pubs récompensées (cycle couple + crédits bonus)
import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models
from django.utils import timezone


def migrate_ad_rewards_forward(apps, schema_editor):
    """Transfère granted_by vers user si des lignes existent."""
    AdReward = apps.get_model("payments", "AdReward")
    # order_by('pk') évite Meta.ordering sur earned_at (déjà renommé en created_at)
    for reward in AdReward.objects.order_by("pk"):
        if reward.granted_by_id and not reward.user_id:
            reward.user_id = reward.granted_by_id
            reward.completed = True
            reward.completed_at = reward.created_at or timezone.now()
            reward.reward_type = "rewarded_video"
            reward.credits_applied = True
            if not reward.reward_cycle_id:
                reward.reward_cycle_id = uuid.uuid4()
            reward.save(
                update_fields=[
                    "user_id",
                    "completed",
                    "completed_at",
                    "reward_type",
                    "credits_applied",
                    "reward_cycle_id",
                ]
            )


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_couple_daily_usage"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="coupledailyusage",
            name="extra_questions",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Questions bonus débloquées via pubs récompensées.",
            ),
        ),
        migrations.AddField(
            model_name="adreward",
            name="reward_cycle_id",
            field=models.UUIDField(db_index=True, default=uuid.uuid4),
        ),
        migrations.AddField(
            model_name="adreward",
            name="completed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="adreward",
            name="reward_type",
            field=models.CharField(
                choices=[("rewarded_video", "Vidéo récompensée")],
                default="rewarded_video",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="adreward",
            name="credits_applied",
            field=models.BooleanField(
                default=False,
                help_text="True lorsque le couple a reçu les questions bonus.",
            ),
        ),
        migrations.AddField(
            model_name="adreward",
            name="completed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="adreward",
            name="user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ad_rewards",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RenameField(
            model_name="adreward",
            old_name="earned_at",
            new_name="created_at",
        ),
        migrations.AlterModelOptions(
            name="adreward",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "récompense pub",
                "verbose_name_plural": "récompenses pub",
            },
        ),
        migrations.RunPython(migrate_ad_rewards_forward, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="adreward",
            name="granted_by",
        ),
        migrations.AlterField(
            model_name="adreward",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="ad_rewards",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="adreward",
            unique_together={("reward_cycle_id", "user")},
        ),
    ]
