# 🎯 Onboarding Accéléré — K'er

**Objectif:** Être productif en 2 heures  
**Durée estimée:** 120 minutes  
**Prerequis:** Python 3.10+, Git, VSCode

---

## ⏱️ Étape 1 : Préparation (15 min)

### 1.1 — Cloner & Venv
```bash
cd d:\projects  (ou votre dossier de travail)
git clone <repo> K_er
cd K_er

# Créer venv
python -m venv .venv
.venv\Scripts\activate    # Windows
# source .venv/bin/activate  # MacOS/Linux

# Installer dépendances
pip install -r requirements.txt
```

### 1.2 — Config `.env`
```bash
# Copier template
copy .env.example .env    # Windows
# cp .env.example .env    # MacOS/Linux

# Éditer avec VSCode
code .env
```

**Contenu minimal `.env`:**
```env
DEBUG=True
SECRET_KEY=dev-change-in-production

# IA : Mode "static" = pas de clé API requise
AI_PROVIDER=static

# Si vous voulez tester Gemini plus tard :
# AI_PROVIDER=gemini
# GEMINI_API_KEY=votre-clé-google
# GEMINI_MODEL=gemini-2.0-flash

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# Game config (optionnel, défauts OK)
GAME_AUTO_NEXT_SECONDS=10
QUESTIONS_PER_LEVEL=21
```

---

## ⏱️ Étape 2 : Database & Data (20 min)

```bash
# Migrations
python manage.py migrate

# Seed les 1000 questions de banque
python manage.py seed_question_bank

# Créer super-user (admin)
python manage.py createsuperuser
# Username: admin
# Email: admin@local
# Password: admin123
```

### Vérifier la DB
```bash
python manage.py dbshell
# Ou simplement ouvrir db.sqlite3 dans VSCode SQL extension
```

---

## ⏱️ Étape 3 : Lancer les Serveurs (10 min)

### **Terminal 1 — Django + WebSocket (Daphne)**
```bash
daphne -b 0.0.0.0 -p 8000 config.asgi:application
# Sortie:
# 2025-05-16 14:23:45,123 daphne.server Listening on 127.0.0.1:8000

# URL: http://localhost:8000/
```

### **Terminal 2 — Redis** (si vous avez Redis localement)
```bash
redis-server
# Ou passer si Redis non-local (DEV peut tourner sans)
```

### **Terminal 3 — Celery Worker** (optionnel mais recommandé)
```bash
celery -A config worker -l info
# Permet la pré-génération asynchrone de questions
```

✅ **Si seulement Terminal 1 → OK pour commencer, questions un peu plus lentes**

---

## ⏱️ Étape 4 : First Run — Créer un Couple Test (15 min)

### 4.1 — Admin pour vérifier data
```bash
# Dans navigateur: http://localhost:8000/admin/
# Login: admin / admin123
```

Parcourir:
- **Users** → 1 utilisateur (l'admin)
- **Questions** → ~1000 questions (banque)
- **Couples** → (vide pour l'instant)

### 4.2 — Créer 2 utilisateurs pour test
**Option A: Via Django Shell** (rapide)
```bash
python manage.py shell

from apps.users.models import User

user1 = User.objects.create_user(
    username='alice',
    password='test123',
    display_name='Alice ❤️'
)

user2 = User.objects.create_user(
    username='bob',
    password='test123',
    display_name='Bob 💙'
)

print(f"Users créés: {user1.label}, {user2.label}")
exit()
```

**Option B: Via Signup UI** (à travers l'app)
- Visiter `http://localhost:8000/users/signup/`
- Créer alice, puis bob
- Confirmer emails (dev: pas de vérification requise)

### 4.3 — Tester le Flow
```
1. Login comme alice
   → http://localhost:8000/couple/setup/
   → Cliquer "Créer une room"
   → Copier code (ex: ABC123)

2. Logout
   → http://localhost:8000/users/logout/

3. Login comme bob
   → http://localhost:8000/couple/setup/
   → Entrer code ABC123 → Rejoindre

4. Boom! 💥 WebSocket connecté
   → Vous êtes dans une session en temps réel!

5. Cliquer "Commencer la session"
   → Alice voit question
   → Bob voit question

6. Répondre → Voir réponse partenaire → Score

7. Recommencer!
```

---

## ⏱️ Étape 5 : Explorer le Code (20 min)

### 5.1 — Arborescence Clé
```
K_er/
├── apps/
│   ├── users/                   # Auth
│   ├── couples/                 # Room + WebSocket
│   ├── game/                    # Core engine
│   │   ├── services/
│   │   │   ├── game_engine.py       ← LIRE EN PRIORITÉ
│   │   │   ├── compatibility_engine.py
│   │   │   └── ...
│   │   ├── models.py                ← Modèles
│   │   └── consumers/               ← WebSocket
│   ├── ai/                      # Gemini + Static provider
│   ├── payments/                # Freemium
│   └── notifications/           # Stub
├── config/
│   ├── settings/
│   │   └── base.py              ← Config globale
│   ├── asgi.py                  ← WebSocket routing
│   └── urls.py                  ← URL patterns
├── templates/                   # HTML + Jinja2
├── static/                      # CSS, JS, PWA
├── db.sqlite3                   ← Base de donnees
└── ANALYSE_SENIOR.md            ← Documentation complète
```

### 5.2 — Fichiers à Lire En Ordre

**Jour 1 - Fondamentaux (30 min)**
1. `apps/game/services/game_engine.py` (40 lignes, cœur du jeu)
2. `apps/game/models.py` (modèles Question, Answer, Session)
3. `apps/couples/consumers.py` (WebSocket entry point)

**Jour 1 - Services Métier (30 min)**
4. `apps/game/services/compatibility_engine.py` (scoring)
5. `apps/ai/services/service.py` (façade IA)
6. `apps/couples/services.py` (logique couple)

**Jour 2 - Infrastructure**
7. `config/asgi.py` (WebSocket routing)
8. `apps/game/tasks.py` (Celery)
9. `apps/payments/models.py` (freemium)

---

## ⏱️ Étape 6 : Comprendre WebSocket (15 min)

### 6.1 — Debug WebSocket en Direct

**Ouvrir DevTools Chrome:**
```
F12 → Application → Cookies → Voir session
                 → Storage → IndexedDB
→ On peut même "Network tab → WS" voir tous les messages WebSocket!
```

### 6.2 — WebSocket Flow Visuel
```
Client 1 (Alice)                 Client 2 (Bob)
    │                               │
    └─ ws://localhost:8000/ws/ABC123/ ┘
            │         │         │
            └─ GROUP: couple_ABC123 ─┘


Event Flow:
┌─────────────────────────────────────────────┐
│ Alice clicks "Start Session"                │
├─────────────────────────────────────────────┤
│ → send_json({"type": "start_session"})      │
│                                             │
│ → Consumer.receive_json()                   │
│    → GameRealtimeService.handle_event()     │
│       → GameEngine.create_question_via_ai() │
│       → return {'broadcast': {...}}         │
│                                             │
│ → channel_layer.group_send()                │
│    → Delivers to Alice AND Bob               │
│                                             │
│ Both see: {"type": "question_ready", ...}   │
└─────────────────────────────────────────────┘
```

---

## ⏱️ Étape 7 : Faire un Petit Change (20 min)

### 7.1 — Easy Change: "Reset Couple Score"

**Objectif:** Ajouter bouton admin pour reset le score d'un couple

**Fichier:** `apps/couples/admin.py`

```python
from django.contrib import admin
from .models import Couple

@admin.action(description="Réinitialiser score")
def reset_score(modeladmin, request, queryset):
    for couple in queryset:
        couple.compatibility_score = 50
        couple.level = 1
        couple.save()
    modeladmin.message_user(request, f"{queryset.count()} couples réinitialisés")

@admin.register(Couple)
class CoupleAdmin(admin.ModelAdmin):
    list_display = ['room_code', 'user1', 'user2', 'compatibility_score', 'level']
    actions = [reset_score]  # ← Ajouter cette ligne
```

**Test:**
1. Aller admin → Couples
2. Sélectionner un couple
3. Dropdown "Action" → "Réinitialiser score"
4. Submit → Done! ✅

### 7.2 — Medium Change: "Nouvelle Catégorie Question"

1. Ajouter choix dans `apps/game/models.py`:
```python
class QuestionCategory(models.TextChoices):
    # Existants...
    CUSTOM = "custom", "Personnalisée"  # ← NEW
```

2. Migrer:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Test: Aller admin → Questions → créer question avec catégorie "Personnalisée"

---

## 🧪 Étape 8 : Lancer Tests (10 min)

```bash
# Tous les tests
python manage.py test

# Tests d'une app
python manage.py test apps.game

# Tests avec verbosité
python manage.py test apps.game -v 2

# Un test spécifique
python manage.py test apps.game.tests.GameEngineTest.test_question_generation
```

**Créer votre premier test:**

Fichier: `apps/game/tests/test_custom.py`
```python
from django.test import TestCase
from apps.users.models import User
from apps.couples.models import Couple
from apps.game.services import GameEngine

class MyFirstTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='test123'
        )
        self.couple = Couple.objects.create(user1=self.user)
    
    def test_couple_creation(self):
        self.assertIsNotNone(self.couple.room_code)
        self.assertEqual(self.couple.compatibility_score, 50)

# Lancer:
# python manage.py test apps.game.tests.test_custom.MyFirstTest.test_couple_creation
```

---

## 🔍 Étape 9 : Déboguer en Pro (15 min)

### 9.1 — Breakpoints VSCode
```python
# Dans app/game/services/game_engine.py, ligne 50

import pdb; pdb.set_trace()  # ← Ajouter cette ligne

# Ou utiliser VSCode Debugger (mieux):
# 1. Create .vscode/launch.json:
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Django",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/manage.py",
            "args": ["runserver"],
            "django": true
        }
    ]
}

# 2. F5 pour lancer debugger
# 3. Click à gauche des ligne numbers pour ajouter breakpoints
# 4. Inspecter variables en hover ou console
```

### 9.2 — Logs
```python
# Dans n'importe quel service:
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug: " + str(data))
logger.info("Info: operation started")
logger.error("Error: " + str(e))

# Dans settings/base.py:
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

---

## 🚀 Étape 10 : Prochaines Steps (Auto-suffisant!) (5 min)

Vous êtes **prêt à développer** ! 🎉

### Que faire maintenant:

✅ **Tâches Recommandées:**
1. Lire [ANALYSE_SENIOR.md](ANALYSE_SENIOR.md) entièrement (référence complète)
2. Explore `apps/game/services/compatibility_engine.py` → Comprendre algo scoring
3. Jouer une session en écoutant les logs (Terminal 1)
4. Ajouter une nouvelle petite feature (ex: nouveau badge)
5. Écrire un test pour votre feature
6. Merger via Pull Request
7. Célébrer! 🎊

✅ **Si Vous Trouvez un Bug:**
1. Créer une branche: `git checkout -b fix/bug-name`
2. Localiser service responsable
3. Ajouter test pour reproduire
4. Fixer
5. Vérifier autres tests non-cassés: `python manage.py test`
6. Commit + PR

✅ **Si Vous Ajoutez Feature:**
1. Design dans `services.py` en priorité
2. Écrire tests AVANT le code (TDD)
3. Implement
4. Vérifier WebSocket si sync requise
5. Doc dans docstrings
6. PR

---

## 📚 Cheat Sheet Rapide

### Django Shell
```bash
python manage.py shell

# Import tout
from apps.users.models import User
from apps.game.models import *
from apps.couples.models import Couple

# Créer objet
u = User.objects.create_user('alice', 'pass')

# Query
couples = Couple.objects.all()
couple = Couple.objects.get(room_code='ABC123')

# Update
couple.level = 5
couple.save()

# Delete
couple.delete()

# Admin
u.is_staff = True
u.is_superuser = True
u.save()
```

### URLs Utiles
```
Admin:                  http://localhost:8000/admin/
Welcome:                http://localhost:8000/
Setup (créer/rejoindre): http://localhost:8000/couple/setup/
Dashboard:              http://localhost:8000/couple/dashboard/
Game session:           http://localhost:8000/couple/waiting/<CODE>/
```

### Terminal Hotkeys
```
Ctrl+C                  Stop server
Ctrl+Shift+C            Copy
Ctrl+V                  Paste
cls                     Clear screen (Windows)
clear                   Clear screen (MacOS/Linux)
```

---

## ❓ FAQ Onboarding

**Q: Redis obligatoire?**  
A: Non, dev peut tourner sans. Mais Celery + WebSocket production requièrent Redis.

**Q: Pourquoi "daphne" et pas "python manage.py runserver"?**  
A: `daphne` supporte WebSocket Channels. `runserver` standard ne le fait pas.

**Q: Où est l'IA?**  
A: Mode static (défaut) = banque 1000 Q. Mode Gemini = API externe (ajouter clé .env).

**Q: Comment déboguer WebSocket?**  
A: DevTools Chrome (F12 → Network → WS) voir tous les messages. Ou logs dans Consumer.

**Q: Je peux commit sans passer tests?**  
A: Non! Toujours: `python manage.py test` avant push.

**Q: Où trouver les logs d'erreur?**  
A: Terminal 1 (Django), Terminal 3 (Celery). Ou Django admin → Logs (si configured).

---

## 🎓 Ressources

- **Django Docs:** https://docs.djangoproject.com/ (Python web framework)
- **Django Channels:** https://channels.readthedocs.io/ (WebSocket support)
- **Celery:** https://docs.celeryproject.org/ (async tasks)
- **PostgreSQL:** https://www.postgresql.org/docs/ (prod database)
- **Redis:** https://redis.io/documentation (cache + broker)

---

## 📞 Support Intégration

**Vous êtes bloqué?** Checklist:

- [ ] Tous les terminals lancés? (Django, Redis, Celery)
- [ ] `.env` configuré? (DEBUG=True, AI_PROVIDER=static)
- [ ] Migrations appliquées? (`python manage.py migrate`)
- [ ] Questions seedées? (`python manage.py seed_question_bank`)
- [ ] User créé? (Admin ou `python manage.py createsuperuser`)
- [ ] Redis running? (Port 6379)
- [ ] Logs lisibles? (Terminal outputs clairs)

**Si bloquer:** Vérifier ANALYSE_SENIOR.md section "Dépannage Courant"

---

## ✅ Success Criteria — Vous Êtes Ready When:

- [x] Vous pouvez lancer `daphne` sans erreur
- [x] Vous pouvez créer 2 users et jouer une session
- [x] Vous comprenez WebSocket flow (consumer → service)
- [x] Vous avez lu `ANALYSE_SENIOR.md`
- [x] Vous savez comment lancer tests
- [x] Vous pouvez localiser et lire un service (ex: `game_engine.py`)
- [x] Vous avez ajouté une petite feature custom (bonus!)
- [x] Vous connaissez les 3 patterns clés (logique → services, IA → facad, WebSocket → consumer+service)

**Bravo! 🎉 Vous êtes un dev K'er!**

---

*Durée réelle de ce guide: ~2 heures pour début complet.*  
*Temps pour première contribution: ~4-6 heures après ce guide.*  
*Temps pour être 100% autonome: ~2 semaines de travail.*
