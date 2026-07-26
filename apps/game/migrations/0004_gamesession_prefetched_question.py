from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0003_alter_answer_reaction"),
    ]

    operations = [
        migrations.AddField(
            model_name="gamesession",
            name="prefetched_question",
            field=models.ForeignKey(
                blank=True,
                help_text="Question pré-générée par Gemini pendant le reveal.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to="game.question",
            ),
        ),
    ]
