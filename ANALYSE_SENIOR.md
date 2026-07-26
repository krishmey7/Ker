# K'er - Analyse Complète Senior 🎮💑

**Dernière mise à jour:** Mai 2026  
**Résumé:** PWA Django temps réel pour couples avec IA Gemini, WebSocket, Celery et système freemium

---

## 🎯 Vue d'Ensemble Executive

**K'er** est une **application de jeux relationnels** basée sur des questions secrètes et révélations simultanées. L'UX repose sur la synchronisation temps réel via **WebSocket** + **Redis**, l'IA via **Google Gemini**, et la monétisation sur un modèle **freemium + publicités récompensées**.

### Points Forts Architecturaux
- ✅ **Séparation claire métier/présentation** : toute logique réside dans `services.py`
- ✅ **WebSocket asynchrone** : deux utilisateurs connectés simultanément = sync temps réel
- ✅ **IA découplée** : mode `static` (banque 1000 Q) ou `gemini` (génération dynamique)
- ✅ **PWA complète** : offline, manifest, service worker, installable
- ✅ **Tâches asynchrones** : Celery pour pré-génération questions + avancement auto

---

## 📚 Stack Technique

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend                                                     │
│ - Django Templates (Jinja2)                                 │
│ - HTMX (requêtes partielles)                                │
│ - Alpine.js (interactivité légère)                          │
│ - Tailwind CSS (styling)                                    │
│ - Service Worker (offline, PWA)                             │
└─────────────────────────────────────────────────────────────┘
           ↓ WebSocket + HTTP ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend                                                      │
│ - Django 5.x                                                │
│ - Django Channels (WebSocket)                               │
│ - Celery 5.4+ (async tasks)                                 │
│ - Redis (broker, layers, cache)                             │
│ - PostgreSQL (prod) / SQLite (dev)                          │
└─────────────────────────────────────────────────────────────┘
           ↓ API ↓
┌─────────────────────────────────────────────────────────────┐
│ Services Externes                                            │
│ - Google Gemini (google-genai SDK)                          │
│ - Stripe (stub paiements)                                   │
└─────────────────────────────────────────────────────────────┘
```

### Versions Clés
- **Django:** 5.0+
- **Channels:** 4.0+ (WebSocket)
- **Celery:** 5.4+ (async tasks)
- **Redis:** 5.0+ (broker + channel layer)
- **Gemini SDK:** google-genai >= 1.0.0

---

## 🏛️ Architecture des 6 Apps

### 1. **`apps.users`** — Authentification

**Responsabilité:** Auth, profils utilisateur, avatars

| Composant | Détail |
|-----------|--------|
| **Model** | `User` (extends `AbstractUser`) avec `display_name`, `avatar_emoji` |
| **Views** | `LoginView`, `SignupView`, redirects |
| **URL Namespace** | `users:` |
| **Dépendances** | Django auth standard, aucune externe |

**Flux clé:**
```python
# Enregistrement → Connexion → Dashboard
POST /users/signup/ → GET /users/login/ → GET /couple/dashboard/
```

**Points d'attention:**
- Utilisateur doit être authentifié pour accéder aux rooms
- `User.label` = affichage préféré en UI (emoji + display_name)

---

### 2. **`apps.couples`** — Gestion de Rooms Privées

**Responsabilité:** Création/jonction de rooms, state couple (level, score, streak)

#### Modèles
```python
class Couple(models.Model):
    user1, user2           # Les deux partenaires
    room_code              # Code 6 caractères unique (ex: "ABC123")
    level                  # Progression (1→N)
    compatibility_score    # 0-100, mis à jour après chaque reveal
    streak_days            # Jours consécutifs joués
    last_played_at         # DateField pour calcul streak
```

#### Services (`CoupleService`)
```python
# Créer une room
couple = CoupleService.create_room(user)  # Retourne existante ou crée neuve

# Rejoindre une room
couple = CoupleService.join_room(user, "ABC123")  # Assigne user2

# Récupérer couple actif
couple = CoupleService.get_active_couple(user)  # Couple complet

# Mise à jour streak (appelée après chaque session)
CoupleService.update_streak(couple)
```

#### WebSocket Consumer (`GameRoomConsumer`)
- **URL:** `ws://localhost:8000/ws/couple/<CODE>/`
- **Events:** `answer_submitted`, `start_session`, `next_question`, `reaction`, etc.
- **Groupe Channels:** `couple_<ROOM_CODE>`

**Important:** Consumer valide l'authentification ET l'appartenance au couple.

---

### 3. **`apps.game`** — Moteur de Jeu

**Responsabilité:** Sessions, questions, réponses, calcul compatibilité, gamification

#### Modèles Core

```python
class GameSession:
    couple                  # Foreign key Couple
    current_question_index  # Index interne
    status                  # LOBBY, QUESTION, WAITING_REVEAL, REVEAL, FINISHED
    current_question        # FK Question actuelle
    prefetched_question     # Question pré-générée pour la suivante (Celery)
    game_mode              # SECRET_ANSWER, GUESS_PARTNER, TIMED, etc.
    category_filter        # Catégorie forcée (ou vide = aléatoire)
    
class Question:
    text                    # Texte de la question
    category               # romantic, funny, spicy, deep, know_partner, future, habits
    spicy_level            # 0 (normal) ou 1 (spicy)
    is_ai_generated        # True = Gemini, False = banque admin
    is_active              # Désactiver questions anciennes/mauvaises
    
class Answer:
    session, question, user # Clés
    text                    # Réponse du partenaire (secrète)
    guess_text             # Devinette du partenaire
    reaction               # Emoji réaction (😍, 😂, 🔥, etc.)
    
class QuestionRound:
    couple, session, question  # Historique
    compatibility_percent      # 0-100, calculé par moteur local
    compatibility_insight      # Texte enrichi par IA
```

#### Flux Jeu Standard (5 étapes)

```
1. START_SESSION (client)
   → GameEngine.generate_next_question()
   → Question chargée
   → Broadcast: "question_ready" + texte

2. ANSWER_SUBMITTED (user1 + user2)
   → Enregistrer Answer pour chaque user
   → Attendre 2 réponses
   → Quand user2 arrive = Broadcast "both_answered"

3. REVEAL (délai 2-3s pour suspense)
   → Afficher les 2 réponses side-by-side
   → CompatibilityEngine calcule score 0-100
   → RelationshipAI enrichit le texte
   → Sauvegarde QuestionRound
   → Celery: prefetch_question_task(session_id)

4. REACTION (optionnel)
   → Users cliquent emoji → Broadcast aux deux

5. NEXT_QUESTION (auto ou manuel)
   → Si prefetched_question chargée = l'utiliser
   → Sinon relancer GameEngine.generate_next_question()
   → Level up si questions_played % 21 == 0
```

#### Services Game (Logique Métier)

**`GameEngine`** — Génération questions
```python
GameEngine.create_question_via_ai(session)
# 1. Mode "static" → QuestionPickerService.pick()
# 2. Mode "gemini" → Gemini API
# 3. Fallback → Banque admin si Gemini indisponible

GameEngine.generate_next_question(session_id)
# Chaine: prefetched → create_via_ai → pick_static
```

**`GameRealtimeService`** — Synchronisation WebSocket
```python
result = GameRealtimeService.handle_event(
    room_code="ABC123",
    user_id=42,
    event_type="answer_submitted",
    payload={"text": "..."}
)
# Retourne {'broadcast': {...}} ou None (erreur)

state = GameRealtimeService.get_room_state(room_code, user_id)
# État complet de la session pour reconnexion
```

**`CompatibilityService`** — Calcul Score
```python
result = CompatibilityService.compute_round_result(
    question_text="...",
    answers_context=[
        {"user_id": 1, "text": "...", "user_label": "Alice"},
        {"user_id": 2, "text": "...", "user_label": "Bob"}
    ]
)
# → {"percent": 75, "insight": "Vous aimez..."}
```

**`QuestionUsageService`** — Anti-doublons
```python
used_texts = QuestionUsageService.get_used_question_texts(couple)
# Retourne set() de tous les textes questions déjà jouées par le couple

is_allowed = QuestionUsageService.is_question_allowed(couple, question)
# True si question jamais vue par le couple
```

---

### 4. **`apps.ai`** — Intégration IA Gemini

**Responsabilité:** Génération contenu via Gemini ou fallback statique

#### Architecture Provider
```
AIService (façade métier)
    ↓
get_provider() → Provider concret
    ├─ GeminiProvider (google-genai SDK)
    └─ StaticProvider (banque 1000 Q)
```

#### Configuration (`.env`)
```env
AI_PROVIDER=gemini              # ou "static"
GEMINI_API_KEY=sk-...           # Clé API obligatoire si provider=gemini
GEMINI_MODEL=gemini-2.0-flash   # Modèle par défaut
AI_REQUEST_TIMEOUT=30           # Secondes
```

#### API AIService
```python
from apps.ai.services import get_ai_service

ai = get_ai_service()

# Générer 1 question
item = ai.generate_question(
    category="romantic",           # Catégorie
    spicy_level=0,                # 0=normal, 1=spicy
    exclude_texts=[...]           # Textes à exclure (antidoublons)
)
# → {"text": "...", "category": "romantic", "spicy_level": 0}

# Générer batch (ex. Celery)
items = ai.generate_questions(category="funny", count=20)

# Enrichir analyse
insight = ai.compatibility_summary(answers_context)

# Phrase émotionnelle
phrase = ai.generate_emotional_phrase()
```

#### Tâches Celery (`apps.ai.tasks`)
```python
from apps.ai.tasks import generate_questions_batch

# Lance génération en arrière-plan
generate_questions_batch.delay(category="romantic", count=50)
```

#### Fallback
- Si Gemini timeout/erreur → **QuestionPickerService** tire de la banque admin
- Si banque vide → Question par défaut en dur

---

### 5. **`apps.payments`** — Freemium & Monétisation

**Responsabilité:** Quota quotidien, abonnements, pubs récompensées, paiements

#### Modèles
```python
class Subscription:
    couple              # OneToOne Couple
    plan_type          # "none" (gratuit), "weekly", "weekend"
    is_active          # État abonnement
    start_date, end_date
    
class PaymentTransaction:
    couple, user       # Transaction historique
    amount, currency
    status             # pending, completed, failed, refunded
    external_id        # ID passerelle (Stripe, etc.)

class DailyUsage:
    user, date         # Compteur quotidien
    questions_played   # Incrémenté après chaque reveal
    bonus_from_ads     # Bonus publicités récompensées
```

#### Limites Freemium (config/settings/base.py)
```python
FREE_DAILY_QUESTIONS = 7                  # Questions gratuites/jour
REWARDED_AD_EXTRA_QUESTIONS = 5           # Bonus par pub regardée
REWARDED_AD_MAX_UNLOCKS_PER_DAY = 10      # Max pubs/jour (50 Q bonus)
WEEKLY_PREMIUM_PRICE = "1.99"             # Premium 7 jours
WEEKEND_PASS_PRICE = "0.50"               # Pass weekend
```

#### Flux Premium
```
Gratuit (7 Q/jour)
    ↓ (quotidien reset)
Regarder pub (5 Q bonus) × 10 max = 50 max bonus
    ↓ (après 10 pubs)
Acheter Weekly (7 jours illimité)
    ↓ (après 7 jours)
Back to gratuit OU auto-renew si actif
```

---

### 6. **`apps.notifications`** — Notifications (Stub)

**Responsabilité:** Push notifications, emails (structure prête)

| Composant | Détail |
|-----------|--------|
| **Model** | `Notification` + `NotificationService` |
| **Status** | Implémentation skeleton, prête pour Twilio/Firebase |
| **Usage** | Rappels quotidiens, matchs de compatibilité |

---

## 🔄 Flux de Données Clés

### Flux WebSocket Complet (Temps Réel)

```
CLIENT (WebSocket)
    │
    ├─→ JSON: {"type": "start_session", "payload": {}}
    │
    └─── CONSUMER (GameRoomConsumer.receive_json)
         │
         ├─→ GameRealtimeService.handle_event()
         │   ├─→ GameEngine.create_question_via_ai()
         │   │   ├─→ Mode static? QuestionPickerService.pick()
         │   │   └─→ Mode gemini? AI.generate_question()
         │   │
         │   ├─→ Enregistrer Question + broadcast
         │   │
         │   └─→ {'broadcast': {...}}
         │
         ├─→ channel_layer.group_send()
         │
         └─→ ALL CLIENTS in couple_<CODE>
            │
            └─── room_event() → send_json()
```

### Flux Answer + Reveal

```
User1 submits Answer
    ↓ (Consumer.receive_json → handle_event)
        ├─→ Answer.objects.create(user=user1, text="...")
        ├─→ Check: user2 answered?
        │   └─→ YES: Broadcast "both_answered"
        │   └─→ NO: Wait (timeout ~30s)
        │
        └─→ Broadcast {"type": "waiting_for_partner"}

(2-3 secondes later)
    ↓ Reveal triggered (client-side delay ou server-side auto)
        ├─→ CompatibilityEngine.compute_score(answers)
        ├─→ RelationshipAI.enrich(insight)
        ├─→ QuestionRound.objects.create(percent=X, insight="...")
        ├─→ Celery: prefetch_question_task(session_id)
        │   └─→ Pré-génère Question suivante en arrière-plan
        │
        └─→ Broadcast {"type": "reveal", "percent": 75, "insight": "..."}

~10 secondes après reveal
    ↓ Auto-advance (configurable GAME_AUTO_NEXT_SECONDS)
        └─→ Celery: auto_advance_after_reveal_task(room_code)
            └─→ Charge prefetched_question ET lance prochaine

Client reconnects
    ↓ WebSocket connect() → send_json(session_state)
        └─→ État complet (Q actuelle, statut, score...)
```

---

## 📊 Modèles de Données (ER Simplifié)

```
┌─────────────┐
│    User     │
│─────────────│
│ id (PK)     │
│ username    │
│ display_name│
│ avatar_emoji│
└────────┬────┘
         │
    ┌────┴──────────────────┐
    │                       │
    │                       │
┌───┴─────────────────┐    │
│   DailyUsage        │    │
│─────────────────────│    │
│ user_id (FK)        │    │
│ date                │    │
│ questions_played    │    │
│ bonus_from_ads      │    │
└─────────────────────┘    │
                           │
                       ┌───┴────────────────┐
                       │                    │
                ┌──────┴─────────┐    ┌────┴──────┐
                │   Couple       │    │    Couple  │
                │─────────────── │    │────────────│
                │ user1_id (FK)  │    │ user2_id(FK)
                │ user2_id (FK)  │    │
                │ room_code      │    │
                │ level          │    │
                │ compatibility_ │    │
                │ score          │    │
                │ streak_days    │    │
                └────────┬───────┘    └────────────┘
                         │
                    ┌────┴────────┐
                    │             │
            ┌───────┴────────┐  ┌─┴──────────────────┐
            │ GameSession    │  │ Subscription       │
            │────────────────│  │────────────────────│
            │ couple_id (FK) │  │ couple_id (FK)     │
            │ current_q_id   │  │ plan_type          │
            │ prefetched_q   │  │ is_active          │
            │ status         │  │ start_date, end_dt │
            │ game_mode      │  │ auto_renew         │
            └────┬───────────┘  └────────────────────┘
                 │
         ┌───────┼──────────┐
         │       │          │
    ┌────┴──┐ ┌──┴─────┐ ┌─┴──────────┐
    │ Answer│ │Question│ │QuestionRound
    │───────│ │────────│ │─────────────
    │session│ │ text   │ │couple_id
    │user   │ │category│ │question_id
    │ text  │ │spicy   │ │compat_pct
    │ guess │ │ai_gen  │ │compat_txt
    │ react │ │ active │ │
    └───────┘ └────────┘ └─────────────┘
```

---

## 🔑 Patterns & Conventions

### 1. **Rule #1 : Logique Métier dans `services.py`**

❌ **MAUVAIS** — Logique dans view
```python
# Dans view
def my_view(request):
    couple = request.user.couples_as_user1.first()
    couple.level += 1
    couple.save()
```

✅ **BON** — Service réutilisable
```python
# Dans service
class CoupleService:
    @staticmethod
    def update_level(couple):
        couple.level += 1
        couple.save()
        return couple

# Dans view
couple = CoupleService.update_level(couple)
```

### 2. **IA = Jamais dans View**

❌ **MAUVAIS** — Appel API direct
```python
def reveal_view(request):
    from google import genai
    response = genai.generate_content(prompt)
```

✅ **BON** — Via façade AIService
```python
from apps.ai.services import get_ai_service
ai = get_ai_service()
insight = ai.compatibility_summary(answers)
```

### 3. **WebSocket = Consumer + Service**

- **Consumer:** Authentification, routage, broadcast
- **Service:** Logique métier (answers, scores, etc.)

```python
# Consumer reçoit JSON
result = GameRealtimeService.handle_event(...)
# Service retourne {'broadcast': {...}}
# Consumer diffuse au groupe
```

### 4. **Anti-doublon Questions**

Toujours vérifier avant d'assigner une question :
```python
if QuestionUsageService.is_question_allowed(couple, question):
    session.current_question = question
    session.save()
```

### 5. **Transactions Atomiques pour Critical Sections**

```python
@transaction.atomic
def join_room(user, code):
    couple = Couple.objects.select_for_update().get(room_code=code)
    # Garantit pas deux jonctions simultanées
    couple.user2 = user
    couple.save()
```

---

## 🎪 Points d'Intégration pour Nouveau Dev

### **Si vous fixez un bug:**

1. **Identifier l'app:** `users/` `couples/` `game/` `ai/` `payments/` `notifications/`
2. **Trouver le service:** `apps/<app>/services.py`
3. **Modifier isolément** le service
4. **Tester localement:** `python manage.py test apps.<app>`
5. **Vérifier WebSocket:** Tester en dev avec deux clients

### **Si vous ajoutez une feature:**

#### Exemple : "Nouvelles questions thématiques"

1. **Ajouter catégorie** → `GameMode.py`
2. **Créer prompt** → `apps/ai/services/prompts.py`
3. **Tester Gemini** → Celery task ou test unitaire
4. **Intégrer UI** → Template + HTMX + Alpine.js
5. **Ajouter quota** → `DailyUsage` logique si premium
6. **WebSocket** → Nouveau event type si sync nécessaire

### **Si vous intégrez une passerelle paiement (Stripe, etc.):**

1. **Modèle:** `apps/payments/models.py` → `PaymentTransaction`
2. **Service:** `apps/payments/services.py` → Logique
3. **View:** Webhook handler
4. **Tasks:** Vérification async si besoin
5. **Tests:** Mock API, pas vraies cartes

---

## ⚙️ Configuration & Démarrage

### **Dev Quickstart**
```bash
# 1. Environnement
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. Config
copy .env.example .env
# Éditer .env :
# DEBUG=True
# AI_PROVIDER=static (ou "gemini" + GEMINI_API_KEY)
# REDIS_URL=redis://127.0.0.1:6379/0

# 3. DB
python manage.py migrate
python manage.py seed_question_bank

# 4. Admin
python manage.py createsuperuser

# 5. Run
# Terminal 1: Django
daphne -b 0.0.0.0 -p 8000 config.asgi:application

# Terminal 2: Celery (optionnel, mais recommandé pour prefetch)
celery -A config worker -l info

# Terminal 3: Redis (si local)
redis-server
```

### **Fichiers .env Clés**
```env
# Core
DEBUG=True
SECRET_KEY=dev-key-123

# IA
AI_PROVIDER=gemini              # ou "static"
GEMINI_API_KEY=<votre-cle>
GEMINI_MODEL=gemini-2.0-flash

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# DB (dev = SQLite, prod = PostgreSQL)
DATABASE_URL=sqlite:///db.sqlite3

# Game config
GAME_AUTO_NEXT_SECONDS=10
QUESTIONS_PER_LEVEL=21
FREE_DAILY_QUESTIONS=7
```

---

## 🧪 Testing Strategy

### **Unit Tests**
```python
# apps/game/tests/test_compatibility.py
class CompatibilityEngineTest(TestCase):
    def test_perfect_match_score(self):
        engine = CompatibilityEngine()
        score = engine.compute(answers_matching_perfectly)
        self.assertEqual(score, 100)
```

### **Integration Tests**
```python
# Test WebSocket full flow
class GameRoomConsumerTest(WebsocketCommunicatorTestCase):
    async def test_answer_flow(self):
        # 1. User1 answers
        # 2. User2 answers
        # 3. Reveal + score
```

### **Run Tests**
```bash
python manage.py test                    # All tests
python manage.py test apps.game          # One app
python manage.py test apps.game.tests.TestName.test_method
```

---

## 📈 Performance & Scalabilité

### **Optimisations en Place**
- ✅ **select_related/prefetch_related:** Queries optimisées
- ✅ **Redis Channel Layer:** WebSocket broadcast sans DB hit
- ✅ **Celery prefetch:** Questions générées hors chemin critique
- ✅ **Question cache:** Banque admin 1000 Q = pas d'attente

### **Goulots Bottlenecks à Surveiller**
- 🔴 **Gemini API:** Timeout 30s, fallback à banque
- 🔴 **Redis down:** WebSocket en mémoire (dev), failures (prod)
- 🔴 **DB:** N+1 queries sur historique sessions
- 🔴 **IA enrichment:** Appel sync bloquant (relever timeout si lent)

### **Monitoring Recommandé**
```python
# Metrics à logger
- Temps réponse Gemini (perf.log)
- Taux erreur questions (debug.log)
- Connexions WebSocket (channels stats)
- Celery task delays (Flower UI)
```

---

## 🛠️ Dépannage Courant

| Problème | Cause Probable | Solution |
|----------|---|---|
| WebSocket connect fail | User pas authentifié | Check `session['_auth_user_id']` |
| Deux mêmes questions | Anti-doublons pas appelé | Vérifier `QuestionUsageService` |
| Gemini timeout | Délai réseau > 30s | Augmenter `AI_REQUEST_TIMEOUT` ou mode static |
| Celery tasks pending | Redis down / worker arrêté | `celery -A config worker` ou `redis-server` |
| PWA offline fail | Service worker pas enregistré | Check browser DevTools → Application → Service Workers |
| Streak pas incrémenté | `update_streak()` pas appelé | Appeler après chaque session terminée |

---

## 📝 Checklist d'Intégration Nouvelle Dev

- [ ] Cloner repo et lancer dev quickstart
- [ ] Créer couple test + jouer une session (WebSocket)
- [ ] Lire `ANALYSE_SENIOR.md` (ce fichier!)
- [ ] Explorer `apps/game/services/game_engine.py` (core)
- [ ] Tester mode Gemini VS mode static
- [ ] Lire tests existants dans `apps/game/tests/`
- [ ] Vérifier Celery worker en arrière-plan
- [ ] Jouer avec Django admin → Questions
- [ ] Étudier `compatibility_engine.py` (algo score)
- [ ] Pratiquer sur petit bug/feature avant intégration majeure
- [ ] Participer à code review avant merge main
- [ ] Documenter toute logique non-évidente dans docstrings
- [ ] Valider que service métier réutilisable, pas dans view

---

## 🚀 Commandes Utiles en Dev

```bash
# Migrations
python manage.py makemigrations
python manage.py migrate

# Shell interactif
python manage.py shell

# Seed questions
python manage.py seed_question_bank --reset-bank

# Logs live
python manage.py runserver --log-level DEBUG

# Celery beat (scheduled tasks)
celery -A config beat -l info

# Django extensions (shell_plus)
pip install django-extensions
python manage.py shell_plus
```

---

## 🎓 Ressources & Points Clés à Approfondir

### **Absolument comprendre :**
1. **WebSocket Channels** → Consumer async + group_send
2. **CompatibilityEngine** → Scoring déterministe local
3. **QuestionUsageService** → Anti-doublons strategy
4. **AIService factory pattern** → Static vs Gemini

### **Approfondir progressivement :**
1. Celery task prefetching (perf)
2. Streak calculations (timezone-aware dates)
3. PWA manifest + service worker (offline)
4. CSRF + HTMX + WebSocket (sécurité)

### **Documentation Externe**
- Django Channels: https://channels.readthedocs.io/
- Celery: https://docs.celeryproject.org/
- Google Gemini SDK: https://ai.google.dev/
- Redis: https://redis.io/docs/

---

## 💡 Notes Finales

**K'er est un projet bien architecturé** avec séparation claire des responsabilités. La règle "logique métier dans services" rend le code maintenable et testable. 

**Points forts pour nouvel intégrateur:**
- Documentation code bien commentée
- Patterns cohérents (Consumer → Service → Model)
- Tests couvrant happy path
- Fallbacks robustes (IA unavailable = banque)

**À rester vigilant:**
- WebSocket sync multi-utilisateur = conditions de course possibles
- IA coûteuse et lente = timeout et fallbacks essentiels
- Redis critique en prod = cache bypass strategies

**Bon code, bon courage! 🚀**

---

*Analyse rédigée : Mai 2026*  
*Prochaine mise à jour recommandée : Après intégration feature majeure*
