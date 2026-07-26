from django.core.management.base import BaseCommand
from apps.game.models import Question


class Command(BaseCommand):
    help = "Supprime toutes les questions de la banque fallback (is_ai_generated=False)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Confirme la suppression sans demander',
        )

    def handle(self, *args, **options):
        # Compte les questions de la banque
        bank_questions = Question.objects.filter(is_ai_generated=False)
        count = bank_questions.count()
        
        if count == 0:
            self.stdout.write(self.style.WARNING('Aucune question de banque à supprimer.'))
            return
        
        self.stdout.write(f'{count} questions de banque trouvées.')
        
        if not options['force']:
            confirm = input('Confirmer la suppression ? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Suppression annulée.'))
                return
        
        # Suppression
        deleted, _ = bank_questions.delete()
        self.stdout.write(self.style.SUCCESS(f'{deleted} questions de banque supprimées avec succès.'))
