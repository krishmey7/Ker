# Migration — plans weekly / weekend et transactions
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def migrate_legacy_premium(apps, schema_editor):
    """Convertit les anciens abonnements premium en plan weekly."""
    Subscription = apps.get_model("payments", "Subscription")
    for sub in Subscription.objects.filter(status="premium"):
        sub.plan_type = "weekly"
        sub.is_active = True
        if sub.expires_at and not sub.end_date:
            sub.end_date = sub.expires_at
        if sub.started_at and not sub.start_date:
            sub.start_date = sub.started_at
        sub.save(update_fields=["plan_type", "is_active", "start_date", "end_date"])


class Migration(migrations.Migration):

    dependencies = [
        ("couples", "0002_initial"),
        ("payments", "0004_rewarded_ads_system"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="subscription",
            name="plan_type",
            field=models.CharField(
                choices=[("none", "Gratuit"), ("weekly", "Premium hebdomadaire"), ("weekend", "Pass weekend")],
                db_index=True,
                default="none",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="subscription",
            name="is_active",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="subscription",
            name="start_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="end_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="subscription",
            name="auto_renew",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="subscription",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="subscription",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[("free", "Gratuit"), ("premium", "Premium Couple"), ("expired", "Expiré")],
                default="free",
                max_length=16,
            ),
        ),
        migrations.RunPython(migrate_legacy_premium, migrations.RunPython.noop),
        migrations.CreateModel(
            name="PaymentTransaction",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("plan_type", models.CharField(choices=[("none", "Gratuit"), ("weekly", "Premium hebdomadaire"), ("weekend", "Pass weekend")], max_length=16)),
                ("status", models.CharField(choices=[("pending", "En attente"), ("completed", "Complété"), ("failed", "Échoué"), ("refunded", "Remboursé")], default="pending", max_length=16)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=8)),
                ("currency", models.CharField(default="USD", max_length=8)),
                ("external_id", models.CharField(blank=True, max_length=128)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("couple", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="payments", to="couples.couple")),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payment_transactions", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "transaction",
                "verbose_name_plural": "transactions",
                "ordering": ["-created_at"],
            },
        ),
    ]
