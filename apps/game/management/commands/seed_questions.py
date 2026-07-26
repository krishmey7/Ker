"""Commande legacy — redirige vers la banque de 1000 questions."""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Charge la banque fallback (1000 questions). Alias de seed_question_bank."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Utilisez seed_question_bank pour la banque complète."))
        call_command("seed_question_bank")
