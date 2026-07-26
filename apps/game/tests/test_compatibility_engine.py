"""Tests du moteur de compatibilité déterministe."""
from django.test import SimpleTestCase

from apps.game.services.compatibility_engine import CompatibilityEngine


class CompatibilityEngineTests(SimpleTestCase):
    def test_exact_match_high_score(self):
        ctx = [
            {"label": "A", "text": "J'adore voyager"},
            {"label": "B", "text": "J'adore voyager"},
        ]
        result = CompatibilityEngine.calculate("Voyage ?", ctx)
        self.assertGreaterEqual(result.percent, 70)
        self.assertTrue(result.exact_match)

    def test_shared_travel_theme(self):
        ctx = [
            {"label": "A", "text": "Je veux voyager souvent"},
            {"label": "B", "text": "J'adore découvrir le monde"},
        ]
        result = CompatibilityEngine.calculate("Vos projets ?", ctx, category="future")
        self.assertIn("travel", result.matched_themes)
        self.assertGreaterEqual(result.percent, 55)

    def test_tension_lowers_score(self):
        ctx = [
            {"label": "A", "text": "Je veux me marier bientôt oui"},
            {"label": "B", "text": "Non au mariage, pas prêt jamais"},
        ]
        result = CompatibilityEngine.calculate("Mariage ?", ctx)
        self.assertLess(result.percent, 55)

    def test_positive_alignment_boosts(self):
        ctx = [
            {"label": "A", "text": "Oui j'adore absolument"},
            {"label": "B", "text": "Oui moi aussi vraiment"},
        ]
        result = CompatibilityEngine.calculate("Humeur ?", ctx)
        self.assertGreaterEqual(result.percent, 55)
