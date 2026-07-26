# K'er — PWA jeux de couple en temps réel

Application d'interaction émotionnelle pour couples : réponses secrètes, révélation simultanée, réactions en direct.

## Stack

- **Backend** : Django 5+, Django Channels, Celery
- **DB** : SQLite (dev) / PostgreSQL (prod)
- **Temps réel** : WebSockets + Redis (prod) / InMemory (dev)
- **Frontend** : Django Templates, HTMX, Alpine.js, Tailwind CSS
- **PWA** : manifest, service worker (offline), prompt d'installation
- **IA** : Groq en priorité (`llama-3.3-70b-versatile`), banque locale en fallback

## Démarrage rapide

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python manage.py migrate
python manage.py seed_question_bank
python manage.py createsuperuser
python manage.py runserver
```

Pour le WebSocket en dev (sans Redis) :

```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Celery (optionnel) :

```bash
celery -A config worker -l info
```

## Architecture

```
apps/
  users/          # Auth
  couples/        # Room privée + WebSocket consumer
  game/           # Sessions, questions, reveal (services)
  ai/             # Génération batch (static / Gemini)
  payments/       # Freemium, pubs, premium
  notifications/  # Push (stub)
```

**Règle** : toute logique métier vit dans `services.py`, jamais dans les views/consumers.

## Flow WebSocket

`ws/couple/<CODE>/`

| Événement client | Effet serveur |
|------------------|---------------|
| `start_session` | Nouvelle question |
| `answer_submitted` | Attend 2 réponses → `reveal` |
| `reaction` | Emoji en direct |
| `next_question` | Question suivante |

## Banque de questions fallback (1000)

- **1000 questions** réparties par thème (`romantic`, `funny`, `spicy`, `deep`, `know_partner`, `future`, `habits`)
- Gérables dans **Django Admin** → Questions (`is_ai_generated=False` = banque)
- **Jamais deux fois** la même question pour un couple (`QuestionUsageService`)
- Utilisées quand l'IA (Groq) est indisponible ou si `AI_PROVIDER=static`

```bash
python manage.py seed_question_bank
# optionnel : --reset-bank pour désactiver l'ancienne banque avant réimport
```

## Compatibilité couple (hybride)

Le **score** (0–100) est calculé par un **moteur déterministe** local (`CompatibilityEngine`) : **45+ thèmes**, polarité positive/négative, similarité, tensions, complémentarité.

L'**IA** (`RelationshipAI`) enrichit uniquement le **texte d'analyse** — elle ne décide jamais du pourcentage. Si Gemini est indisponible, l'app affiche le résumé local + un conseil du jour.

```
Réponses → CompatibilityEngine (score) → RelationshipAI (analyse) → reveal
```

## IA — Groq (prioritaire)

Configuration dans `.env` :

```env
AI_PROVIDER=groq
GROQ_API_KEY=votre-cle-groq
GROQ_MODEL=llama-3.3-70b-versatile
AI_REQUEST_TIMEOUT=30
```

Clé API : [console.groq.com](https://console.groq.com/keys)

Modèles alternatifs : `llama-3.1-8b-instant` (plus rapide), `mixtral-8x7b-32768`.

Gemini reste disponible en legacy : `AI_PROVIDER=gemini` + `GEMINI_API_KEY`.

Usage en code (jamais dans les views) :

```python
from apps.ai.services import get_ai_service

ai_service = get_ai_service()
question = ai_service.generate_question(category="romantique")
phrase = ai_service.generate_emotional_phrase(context="après reveal")
```

Test CLI :

```bash
python manage.py generate_ai_question --category romantique
```

Batch Celery :

```bash
celery -A config worker -l info
# puis generate_questions_batch.delay("romantic", 20)
```

## PWA — installation et hors ligne

- Manifest : `/manifest.json`
- Service worker : `/service-worker.js` (scope `/`)
- Page offline : `/offline/`

Générer le logo et les icônes depuis `static/images/logo.png` :

```bash
python manage.py generate_pwa_assets
```

Remplacez `static/images/logo.png` par votre visuel, puis relancez la commande.

## Prochaines étapes

- [x] Icônes PWA (`static/images/icons/`)
- [ ] SDK pub récompensée + Stripe
- [ ] Web Push (VAPID + pywebpush)
- [ ] PostgreSQL + Redis en production
