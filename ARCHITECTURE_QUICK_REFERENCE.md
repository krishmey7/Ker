# 🏗️ Architecture Visuelle & Quick Reference

---

## Architecture Haute Niveau

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENTS (PWA)                                  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │  Browser (Chrome, Safari, etc.)                                  │   │
│  │  • Service Worker (offline)                                      │   │
│  │  • Alpine.js (DOM interactivity)                                 │   │
│  │  • HTMX (partial page updates)                                   │   │
│  │  • Tailwind CSS (styling)                                        │   │
│  │                                                                  │   │
│  │  ┌── ws://localhost:8000/ws/couple/<CODE>/ ──┐                 │   │
│  │  │ WebSocket Connection (Real-time Sync)     │                 │   │
│  │  └──────────────────────────────────────────┘                 │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│          ↓ HTTP                              ↓ WebSocket                 │
└──────────┬─────────────────────────────────────┬─────────────────────────┘
           │                                     │
    ┌──────┴────────────────┐           ┌──────┴─────────────────┐
    │                       │           │                        │
    ▼                       ▼           ▼                        ▼
┌───────────┐          ┌──────────┐  ┌──────────────┐      ┌──────────────┐
│  DJANGO   │  HTTP   │  DAPHNE  │  │   CHANNELS   │      │    REDIS     │
│   VIEWS   │ ────→   │(ASGI SRV)│  │  (WebSocket) │ ←──→ │ (Pub/Sub)    │
│           │         │          │  │              │      │              │
│ ├─ users/ │         └──────────┘  └──────────────┘      └──────────────┘
│ ├─ couples│
│ ├─ game/  │              ▼
│ ├─ ai/    │     ┌─────────────────┐
│ ├─payment │     │ SERVICES LAYER  │
│ └─notify/ │     ├─────────────────┤
│           │     │ GameEngine      │◄──── Logique Métier (OBLIGATOIRE)
│           │     │ CompatibilityEn │
│           │     │ CoupleService   │
│           │     │ AIService       │
│           │     │ PaymentService  │
│           │     └─────────────────┘
│           │           ▼
│           │     ┌────────────────────────┐
│           │     │  DATABASE (SQLite/PG)  │
│           │     ├────────────────────────┤
│           │     │ • Users                │
│           │     │ • Couples              │
│           │     │ • GameSessions         │
│           │     │ • Questions (1000+)    │
│           │     │ • Answers              │
│           │     │ • QuestionRounds       │
│           │     │ • Subscriptions        │
│           │     └────────────────────────┘
│           │
└───────────┘
            ▼
     ┌────────────────┐
     │  CELERY WORKER │
     ├────────────────┤
     │ Async Tasks:   │
     │ • prefetch_Q   │  ◄── Pré-génère questions en background
     │ • auto_advance │  ◄── Avance auto après reveal
     │ • gen_batch    │  ◄── Génère batch de questions
     └────────────────┘
              ▼
     ┌─────────────────────┐
     │  EXTERNAL APIs      │
     ├─────────────────────┤
     │ • Google Gemini     │ ◄── Génère questions IA
     │ • Stripe (stub)     │ ◄── Paiements
     └─────────────────────┘
```

---

## Data Flow — Une Session Complète

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ SESSION FLOW: ALICE & BOB JOUENT UNE QUESTION                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ T=0s: Alice & Bob connectés au WebSocket                                   │
│       ├─ Consumer valide authentification                                  │
│       ├─ group_add() les deux clients au groupe "couple_ABC123"           │
│       └─ Envoie session_state (questions jouées, score, etc.)             │
│                                                                             │
│ T=1s: Alice clique "Démarrer Session"                                      │
│       │                                                                     │
│       ├─ Consumer.receive_json(type="start_session")                       │
│       │   └─ GameRealtimeService.handle_event()                           │
│       │       └─ GameEngine.create_question_via_ai()                       │
│       │           ├─ Mode static? → QuestionPickerService.pick()          │
│       │           │  (tire de la banque 1000 Q)                           │
│       │           ├─ Mode gemini? → Gemini API                            │
│       │           │  (génère question nouvelle)                           │
│       │           └─ Fallback? → Banque                                    │
│       │                                                                     │
│       └─ Question créée/chargée                                            │
│           └─ Broadcast: {"type": "question_ready", "text": "..."}        │
│               │                                                             │
│               ├─ ALICE reçoit JSON                                         │
│               └─ BOB reçoit JSON                                           │
│                                                                             │
│ T=3s: Alice répond "Je t'aime pour ton humour"                            │
│       │                                                                     │
│       ├─ Consumer.receive_json(type="answer_submitted", text="...")       │
│       │   └─ Answer.objects.create(user=alice, text="...")                │
│       │   └─ Check: Bob answered?                                         │
│       │       ├─ Non → Broadcast: {"type": "waiting", "for": "bob"}      │
│       │       └─ Oui → (voir T=8s)                                        │
│       │                                                                     │
│       └─ Alice voit: "En attente de Bob..."                               │
│                                                                             │
│ T=5s: Bob répond "Ton sourire"                                            │
│       │                                                                     │
│       ├─ Answer.objects.create(user=bob, text="...")                      │
│       │                                                                     │
│       └─ BOTH answered! ✅                                                 │
│           └─ Broadcast: {"type": "both_answered"}                         │
│               ├─ ALICE voit: "Révélation dans 2 secondes..."              │
│               └─ BOB voit: "Révélation dans 2 secondes..."                │
│                                                                             │
│ T=7s: (Suspense! ⏳)                                                        │
│                                                                             │
│ T=8s: Reveal! 🎉                                                           │
│       │                                                                     │
│       ├─ CompatibilityEngine.compute_score(answers)                       │
│       │   ├─ Analyse réponses                                             │
│       │   ├─ Polarité (positif/négatif)                                   │
│       │   ├─ Similarité réponses                                          │
│       │   ├─ Thèmes détectés (45+)                                        │
│       │   └─ Score final: 78% ← DÉTERMINISTE, LOCAL                      │
│       │                                                                     │
│       ├─ RelationshipAI.enrich(insight)                                    │
│       │   ├─ Appel Gemini (si disponible)                                 │
│       │   ├─ Retourne texte enrichi: "Vous partagez..."                  │
│       │   └─ Fallback: texte générique si IA indisponible                │
│       │                                                                     │
│       ├─ QuestionRound.objects.create(                                    │
│       │   couple=couple,                                                   │
│       │   compatibility_percent=78,                                        │
│       │   compatibility_insight="Vous partagez..."                         │
│       │ )                                                                   │
│       │                                                                     │
│       ├─ Update Couple.compatibility_score                                │
│       │   (moyenne glissante sur 10 derniers rounds)                      │
│       │                                                                     │
│       ├─ Celery.prefetch_question_task(session_id) ← EN BACKGROUND       │
│       │   (pré-génère Question suivante)                                  │
│       │                                                                     │
│       └─ Broadcast: {"type": "reveal", "percent": 78, "insight": "..."}  │
│           ├─ ALICE: Voit réponse BOB + score                             │
│           └─ BOB: Voit réponse ALICE + score                             │
│                                                                             │
│ T=9s: (Alice peut réagir: 😍, 🔥, 😂)                                      │
│       │                                                                     │
│       ├─ Consumer.receive_json(type="reaction", emoji="😍")               │
│       │   └─ Broadcast: {"type": "reaction", "user": "alice", emoji="..."} │
│       │       └─ BOB voit emoji en temps réel                             │
│       │                                                                     │
│       └─ Reaction.objects.create(...)  (optional, peut être skippé)      │
│                                                                             │
│ T=11s: Cliquer "Question Suivante"                                        │
│       │                                                                     │
│       ├─ Consumer.receive_json(type="next_question")                      │
│       │   └─ GameRealtimeService.handle_event()                           │
│       │       ├─ prefetched_question chargée? → utiliser                  │
│       │       └─ Sinon: relancer GameEngine.create_question_via_ai()     │
│       │                                                                     │
│       └─ Retour à T=1s (nouvelle question)                                │
│                                                                             │
│ Session Terminée après 21 questions:                                      │
│   ├─ Level up: couple.level += 1                                          │
│   ├─ Update streak: CoupleService.update_streak()                         │
│   └─ Possible badge: CoupleBadge.objects.create()                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Class Diagram — Modèles Clés

```
User (Django AbstractUser)
├── username
├── email
├── password_hash
├── display_name ──────┐
├── avatar_emoji       │
└── is_active          │
                       │
                       ▼
              ┌─────────────────┐
              │ Couple (Room)   │
              │─────────────────│
              │ user1 ──────→ User
              │ user2 ──────→ User (nullable)
              │ room_code (unique, 6 chars)
              │ level (1→N)
              │ compatibility_score (0-100)
              │ streak_days
              │ last_played_at
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    ┌─────────────┐ ┌──────────┐ ┌──────────────┐
    │GameSession  │ │Question  │ │Subscription  │
    │─────────────│ │──────────│ │──────────────│
    │couple ──────→ │text      │ │couple ──────→
    │current_q ──→ │category  │ │plan_type
    │prefetched_q  │spicy_lvl │ │is_active
    │status        │ai_gen    │ │start_date
    │game_mode     │is_active │ │end_date
    │category_filt │          │ │auto_renew
    │started_at    └──────┬───┘ └──────────────┘
    │ended_at            │
    └────┬───────────────┼─────────────┐
         │               │             │
         ▼               ▼             ▼
    ┌─────────────┐ ┌──────────────┐ ┌──────────────┐
    │Answer       │ │QuestionRound │ │DailyUsage
    │─────────────│ │──────────────│ │──────────────│
    │session ────→ │couple ──────→ │user ────────→
    │question ───→ │question ────→ │date
    │user ───────→ │compatibility_ │questions_play
    │text        │ │percent (0-100 │bonus_from_ads
    │guess_text  │ │insight       │
    │reaction    │ └──────────────┘ └──────────────┘
    └─────────────┘
```

---

## Services Layer — Responsabilités

```
                    ┌──────────────────────────────────────┐
                    │  CONTROLLERS / VIEWS / CONSUMERS      │
                    │  (Orchestration uniquement)          │
                    └────────────────┬─────────────────────┘
                                     │ Appelle Services
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │                   SERVICES LAYER                           │
        │          (Métier : où vit TOUTE la logique)               │
        ├────────────────────────────────────────────────────────────┤
        │                                                            │
        │ ┌─────────────────────────────────────────────────────┐  │
        │ │ GAME SERVICES (apps/game/services/)                │  │
        │ ├─────────────────────────────────────────────────────┤  │
        │ │ • GameEngine                                        │  │
        │ │   └─ create_question_via_ai()                      │  │
        │ │   └─ generate_next_question()                      │  │
        │ │                                                     │  │
        │ │ • GameRealtimeService                              │  │
        │ │   └─ handle_event(type, payload)                   │  │
        │ │   └─ get_room_state()                              │  │
        │ │                                                     │  │
        │ │ • CompatibilityEngine                              │  │
        │ │   └─ compute_score(answers) → 0-100 %             │  │
        │ │                                                     │  │
        │ │ • QuestionUsageService                             │  │
        │ │   └─ is_question_allowed(couple, q)               │  │
        │ │                                                     │  │
        │ └─────────────────────────────────────────────────────┘  │
        │                                                            │
        │ ┌─────────────────────────────────────────────────────┐  │
        │ │ COUPLE SERVICES (apps/couples/services.py)         │  │
        │ ├─────────────────────────────────────────────────────┤  │
        │ │ • CoupleService                                     │  │
        │ │   └─ create_room(user) → Couple                    │  │
        │ │   └─ join_room(user, code) → Couple                │  │
        │ │   └─ update_streak(couple) → int                   │  │
        │ │                                                     │  │
        │ └─────────────────────────────────────────────────────┘  │
        │                                                            │
        │ ┌─────────────────────────────────────────────────────┐  │
        │ │ AI SERVICES (apps/ai/services/)                    │  │
        │ ├─────────────────────────────────────────────────────┤  │
        │ │ • AIService (Façade)                               │  │
        │ │   └─ get_ai_service() → Provider                   │  │
        │ │   └─ generate_question(cat, spicy) → dict          │  │
        │ │   └─ compatibility_summary(answers) → str          │  │
        │ │                                                     │  │
        │ │ • Provider (Abstract)                              │  │
        │ │   ├─ GeminiProvider ◄── API Google                 │  │
        │ │   └─ StaticProvider ◄── Banque 1000 Q             │  │
        │ │                                                     │  │
        │ └─────────────────────────────────────────────────────┘  │
        │                                                            │
        │ ┌─────────────────────────────────────────────────────┐  │
        │ │ PAYMENT SERVICES (apps/payments/services.py)       │  │
        │ ├─────────────────────────────────────────────────────┤  │
        │ │ • SubscriptionService                              │  │
        │ │   └─ activate_plan(couple, plan_type)              │  │
        │ │   └─ check_quota(couple) → bool                    │  │
        │ │                                                     │  │
        │ └─────────────────────────────────────────────────────┘  │
        │                                                            │
        └────────────────────────────────────────────────────────────┘
                                     │ Lit/Écrit
                                     ▼
        ┌────────────────────────────────────────────────────────────┐
        │                   DATA LAYER                               │
        │              (Models / ORM Django)                         │
        ├────────────────────────────────────────────────────────────┤
        │ User, Couple, GameSession, Question, Answer,              │
        │ QuestionRound, Subscription, DailyUsage, etc.             │
        └────────────────────────────────────────────────────────────┘
```

---

## WebSocket Event Protocol

```
CLIENT → SERVER:
┌──────────────────────────────┐
│ JSON Message Format:         │
│ {                            │
│   "type": "event_name",      │
│   "payload": {               │
│     "key": "value"           │
│   }                          │
│ }                            │
└──────────────────────────────┘

Event Types (Partial List):
┌──────────────────────────────────────────────┐
│ start_session                                │ ← Begin game
├──────────────────────────────────────────────┤
│ answer_submitted                             │ ← Send answer
│ {                                            │
│   "text": "Mon amour pour toi..."           │
│   "guess_text": "..." (optional)            │
│ }                                            │
├──────────────────────────────────────────────┤
│ reaction                                     │ ← Emoji reaction
│ {                                            │
│   "emoji": "😍"                              │
│ }                                            │
├──────────────────────────────────────────────┤
│ next_question                                │ ← Load next Q
├──────────────────────────────────────────────┤
│ ping                                         │ ← Keep-alive
└──────────────────────────────────────────────┘


SERVER → CLIENT (Broadcast):
┌──────────────────────────────────────────────┐
│ "type": "question_ready"                     │ ← New Q loaded
│ {                                            │
│   "text": "...",                             │
│   "category": "romantic",                    │
│   "spicy_level": 0                           │
│ }                                            │
├──────────────────────────────────────────────┤
│ "type": "waiting_for_partner"               │ ← Both click
│ {                                            │
│   "message": "..."                           │
│ }                                            │
├──────────────────────────────────────────────┤
│ "type": "both_answered"                     │ ← Ready 2 reveal
├──────────────────────────────────────────────┤
│ "type": "reveal"                             │ ← Show answers!
│ {                                            │
│   "compatibility_percent": 78,               │
│   "compatibility_insight": "...",            │
│   "your_answer": "...",                      │
│   "partner_answer": "...",                   │
│   "your_label": "Alice"                      │
│ }                                            │
├──────────────────────────────────────────────┤
│ "type": "reaction"                           │ ← Partner emoji
│ {                                            │
│   "from_user": "Bob",                        │
│   "emoji": "🔥"                              │
│ }                                            │
├──────────────────────────────────────────────┤
│ "type": "auto_advance"                       │ ← Next Q auto
│ {                                            │
│   "text": "..."                              │
│ }                                            │
├──────────────────────────────────────────────┤
│ "type": "error"                              │ ← Something wrong
│ {                                            │
│   "message": "Invalid answer"                │
│ }                                            │
└──────────────────────────────────────────────┘
```

---

## File Paths — 30 Fichiers Clés à Connaître

### 🏃 **CRITIQUE — Lire En Priorité (5 fichiers, 1h)**
```
1. apps/game/services/game_engine.py          ← Cœur du jeu
2. apps/game/models.py                        ← Modèles Question/Answer
3. apps/couples/consumers.py                  ← WebSocket entry point
4. apps/game/services/compatibility_engine.py ← Scoring algo
5. apps/ai/services/service.py                ← IA façade
```

### 📚 **IMPORTANT — Comprendre Dans Semaine 1 (10 fichiers, 3h)**
```
6. apps/couples/services.py                   ← Logique couple
7. apps/game/services/realtime.py             ← Time real sync
8. apps/game/tasks.py                         ← Celery tasks
9. config/asgi.py                             ← WebSocket routing
10. apps/payments/models.py                   ← Freemium
11. apps/users/models.py                      ← User model
12. apps/game/models.py (full)                ← All game models
13. apps/game/services/__init__.py            ← Services exports
14. apps/ai/services/factory.py               ← Provider factory
15. apps/game/views.py                        ← Game views
```

### 🎓 **OPTIONAL — Approndir (7 fichiers, 2h)**
```
16. apps/game/services/question_usage_service.py
17. apps/game/services/compatibility_themes.py
18. apps/ai/services/prompts.py
19. apps/game/admin.py
20. apps/couples/urls.py
21. config/settings/base.py
22. apps/game/consumers/game_consumer.py
```

### 📖 **REFERENCE — Consulter Au Besoin**
```
23. apps/notifications/models.py
24. apps/payments/services.py
25. apps/game/context_processors.py
26. apps/couples/models.py (full)
27. apps/users/views.py
28. apps/game/services/compatibility_data.py
29. apps/notifications/services.py
30. apps/payments/views.py
```

---

## Terminal Commands — Cheat Sheet

```bash
# Setup Initial
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_question_bank
python manage.py createsuperuser

# Dev Servers (Run in separate terminals)
daphne -b 0.0.0.0 -p 8000 config.asgi:application     # Server
celery -A config worker -l info                        # Async tasks
redis-server                                            # Cache/broker

# Testing
python manage.py test                                   # All
python manage.py test apps.game                         # One app
python manage.py test apps.game -v 2                   # Verbose
python manage.py test apps.game.tests.TestClass -v 3   # Specific

# Interactive
python manage.py shell
python manage.py shell_plus  # If django-extensions installed
python manage.py dbshell

# Utilities
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_question_bank --reset-bank

# Git
git status
git add .
git commit -m "message"
git push origin branch-name
git pull origin main
```

---

## Configuration Matrix

| Setting | Dev | Production |
|---------|-----|-----------|
| DEBUG | True | False |
| SECRET_KEY | Simple | Complex UUID |
| ALLOWED_HOSTS | 127.0.0.1 | *.example.com |
| DATABASE | SQLite | PostgreSQL |
| REDIS_URL | localhost:6379 | Cluster URL |
| AI_PROVIDER | static | gemini |
| CELERY | Optional | Required |
| CHANNEL_LAYERS | InMemory | Redis |

---

## DRY Principles — Don't Repeat Yourself

### ❌ **Anti-Pattern: Logic in View**
```python
def my_view(request):
    couple = Couple.objects.get(...)
    couple.compatibility_score = 75
    couple.level = 5
    couple.save()
    return render(...)
```

### ✅ **Pattern: Use Service**
```python
# Service (apps/couples/services.py)
class CoupleService:
    @staticmethod
    def update_score_and_level(couple, score, level):
        couple.compatibility_score = score
        couple.level = level
        couple.save()
        return couple

# View
def my_view(request):
    couple = CoupleService.update_score_and_level(couple, 75, 5)
    return render(...)
```

### ✅ **Benefit: Reusable in Celery, Tests, Other Views**
```python
# Celery task reuses same service
@shared_task
def update_couple_stats_task(couple_id, score):
    couple = Couple.objects.get(pk=couple_id)
    CoupleService.update_score_and_level(couple, score, couple.level)

# Test reuses same service
class TestCoupleService(TestCase):
    def test_update_score(self):
        result = CoupleService.update_score_and_level(couple, 75, 5)
        self.assertEqual(result.compatibility_score, 75)
```

---

## Performance Checklist

- [ ] Use `select_related()` for FK queries
- [ ] Use `prefetch_related()` for reverse FK / M2M
- [ ] Add `db_index=True` to frequently filtered fields
- [ ] Cache expensive computations (Redis)
- [ ] Use `only()` / `defer()` to load specific fields
- [ ] Batch operations with `bulk_create()` / `bulk_update()`
- [ ] Monitor N+1 queries with Django Debug Toolbar
- [ ] Use Celery for long-running tasks (>1s)
- [ ] Use `@transaction.atomic()` for critical sections

---

## Security Checklist

- [ ] CSRF tokens in all POST forms
- [ ] Validate user belongs to couple (in consumer + view)
- [ ] Hash passwords (Django handles)
- [ ] Sanitize user inputs (Django ORM does)
- [ ] Use HTTPS in production (Django SECURE_SSL_REDIRECT)
- [ ] Hide SECRET_KEY in .env (never git)
- [ ] SQL injection: Use ORM, never string formatting
- [ ] XSS: Django templates auto-escape
- [ ] CORS: Configure carefully if needed
- [ ] Rate limit API endpoints

---

## Debugging Toolkit

### Print Debugging
```python
import logging
logger = logging.getLogger(__name__)
logger.debug(f"Value: {value}")
logger.info("Start process")
logger.error("Failed", exc_info=True)
```

### Python Debugger
```python
import pdb; pdb.set_trace()  # Breakpoint
# Commands: n (next), c (continue), l (list), p (print)
```

### Django Shell
```python
python manage.py shell
>>> from apps.game.models import Question
>>> q = Question.objects.first()
>>> print(q.text)
```

### Browser DevTools
- F12 → Network → XHR (HTTP requests)
- F12 → Network → WS (WebSocket)
- F12 → Application → Storage (SessionStorage, LocalStorage)
- F12 → Console → JavaScript errors

### Log Tailing
```bash
# Terminal view of Django logs
tail -f logs/django.log

# Or in production:
journalctl -u django-app -f
```

---

## Quick Reference by Task

### "Je dois fixer un bug WebSocket"
1. → Check `apps/game/consumers/game_consumer.py` (receive_json)
2. → Check `apps/game/services/realtime.py` (handle_event)
3. → Add print/logger.debug()
4. → Check browser DevTools → Network → WS tab
5. → Write test to reproduce
6. → Fix service
7. → Test passes ✓

### "Je dois ajouter une feature freemium"
1. → Modify `apps/payments/models.py`
2. → Create migration: `python manage.py makemigrations`
3. → Write check in service: `SubscriptionService.check_quota()`
4. → Call from view/consumer before operation
5. → Add test
6. → Test ✓

### "IA ne répond pas / timeout"
1. → Check `.env` : `AI_PROVIDER=static` ou `GEMINI_API_KEY` valide?
2. → Check logs: `logger.error()` in `AIService`
3. → Aumenter `AI_REQUEST_TIMEOUT` dans settings
4. → Fallback built-in: utilise banque 1000 Q
5. → Check Gemini API status (external)

### "Celery tasks ne s'exécutent pas"
1. → Redis running? `redis-server`
2. → Celery worker running? `celery -A config worker -l info`
3. → Check logs dans Terminal worker
4. → Check task name: `@shared_task(bind=True)`
5. → Test manuellement: `python manage.py shell`
   ```python
   from apps.game.tasks import prefetch_question_task
   prefetch_question_task.delay(session_id=1)
   ```

---

## Glossaire Projet

| Terme | Définition |
|-------|-----------|
| **Couple** | Lien entre 2 utilisateurs, room privée WebSocket |
| **Room Code** | 6 caractères uniques (ex: ABC123) pour rejoindre |
| **GameSession** | Instance de jeu, contient questions/réponses |
| **QuestionRound** | Tour terminé = Question + 2 réponses + score |
| **Compatibility Score** | 0-100%, calculé localement par CompatibilityEngine |
| **Prefetch** | Pré-générer Question suivante en Celery (background) |
| **Static Provider** | Banque 1000 questions (fallback si Gemini down) |
| **Gemini Provider** | Google Gemini API (génération dynamique) |
| **Group Send** | Broadcast message à tous clients dans groupe WebSocket |
| **Consumer** | WebSocket connection handler (async) |
| **Service** | Logique métier réutilisable, pas dans view |
| **Celery** | Task queue async, background jobs |
| **Redis** | Cache + message broker pour Celery/Channels |
| **Daphne** | ASGI server (Django + WebSocket) |

---

## Ressources Rapides

```
Django Docs:        https://docs.djangoproject.com/
Django ORM:         https://docs.djangoproject.com/en/stable/topics/db/
Channels WebSocket: https://channels.readthedocs.io/
Celery Docs:        https://docs.celeryproject.org/
Python Docs:        https://docs.python.org/3/
VSCode Debug:       https://code.visualstudio.com/docs/python/debugging
Git Docs:           https://git-scm.com/doc
PostgreSQL Docs:    https://www.postgresql.org/docs/
Redis Docs:         https://redis.io/documentation
```

---

**Vous avez ce guide? Vous avez tout! 🚀**

*Print pour rester à côté du clavier ou bookmark dans le navigateur.*
