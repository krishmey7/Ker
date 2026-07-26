"""
Charge la banque de 1000 questions fallback (admin : apps.game.Question).
Idempotent : ne duplique pas les textes déjà présents.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.game.data.question_bank import BANK_TARGETS, generate_bank_questions
from apps.game.models import Question


class Command(BaseCommand):
    help = (
        "Charge 1000 questions fallback (Gary Chapman — "
        "« Ce que j'aurais aimé savoir avant de me marier »)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-bank",
            action="store_true",
            help="Désactive les anciennes questions banque (is_ai_generated=False) avant import.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset_bank"]:
            n = Question.objects.filter(is_ai_generated=False).update(is_active=False)
            self.stdout.write(self.style.WARNING(f"{n} questions banque désactivées."))

        try:
            items = generate_bank_questions()
        except ValueError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        created = 0
        skipped = 0
        reactivated = 0

        for item in items:
            obj, was_created = Question.objects.get_or_create(
                text=item["text"],
                defaults={
                    "category": item["category"],
                    "spicy_level": item["spicy_level"],
                    "is_ai_generated": False,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1
                if not obj.is_active:
                    obj.is_active = True
                    obj.is_ai_generated = False
                    obj.save(update_fields=["is_active", "is_ai_generated"])
                    reactivated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Banque : {created} créées, {skipped} déjà présentes ({reactivated} réactivées)."
            )
        )
        for cat, target in BANK_TARGETS.items():
            count = Question.objects.filter(category=cat, is_ai_generated=False, is_active=True).count()
            self.stdout.write(f"  {cat}: {count} actives (cible {target})")
        total = Question.objects.filter(is_ai_generated=False, is_active=True).count()
        self.stdout.write(self.style.SUCCESS(f"Total banque active : {total}"))
