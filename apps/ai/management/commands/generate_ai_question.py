"""Commande — teste la génération IA (Groq/Gemini) depuis le shell."""
from django.core.management.base import BaseCommand

from apps.ai.services import get_ai_service


class Command(BaseCommand):
    help = "Génère une question via le service IA (Groq/Gemini ou fallback)."

    def add_arguments(self, parser):
        parser.add_argument("--category", default="romantique", help="Catégorie (fr ou en)")
        parser.add_argument("--spicy", type=int, default=0, help="Niveau spicy 0-3")

    def handle(self, *args, **options):
        service = get_ai_service()
        self.stdout.write(f"Provider : {service.provider_name}")
        question = service.generate_question(
            category=options["category"],
            spicy_level=options["spicy"],
        )
        self.stdout.write(self.style.SUCCESS(question["text"]))
        self.stdout.write(f"  catégorie={question.get('category')} spicy={question.get('spicy_level')}")
