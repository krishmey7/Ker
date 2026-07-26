"""Champs KibaWallet sur PaymentTransaction."""
import uuid

from django.db import migrations, models


def populate_external_references(apps, schema_editor):
    PaymentTransaction = apps.get_model("payments", "PaymentTransaction")
    for txn in PaymentTransaction.objects.filter(external_reference=""):
        txn.external_reference = f"legacy-{txn.pk}-{uuid.uuid4().hex[:8]}"
        txn.save(update_fields=["external_reference"])


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0005_monetization_plans"),
    ]

    operations = [
        migrations.AddField(
            model_name="paymenttransaction",
            name="provider",
            field=models.CharField(
                choices=[("stub", "Stub (dev)"), ("kibawallet", "KibaWallet")],
                db_index=True,
                default="stub",
                max_length=24,
            ),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="external_reference",
            field=models.CharField(db_index=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="mobile_number",
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="kiba_status",
            field=models.CharField(blank=True, max_length=24),
        ),
        migrations.AddField(
            model_name="paymenttransaction",
            name="kiba_reference",
            field=models.CharField(blank=True, max_length=128),
        ),
        migrations.RunPython(populate_external_references, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="paymenttransaction",
            name="external_reference",
            field=models.CharField(db_index=True, max_length=64, unique=True),
        ),
    ]
