# SkillX ⚡ — Real-Time Skill Exchange Platform

## Stack
- Django 4.2+ · Django Channels 4 · Daphne ASGI · Redis · SQLite

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Redis (required for WebSockets + live queue)
#    macOS:   brew install redis && brew services start redis
#    Ubuntu:  sudo apt install redis-server && sudo systemctl start redis
#    Docker:  docker run -p 6379:6379 redis:alpine

# 3. Run migrations
python manage.py makemigrations
python manage.py migrate

# 4. (Optional) Create admin
python manage.py createsuperuser

# 5. Run with Daphne (ASGI — supports WebSockets)
daphne -p 8000 skillx.asgi:application

# Alternative: python manage.py runserver  (for dev, Daphne preferred)
```

Then open: **http://127.0.0.1:8000/**

## Dev without Redis
In `skillx/settings.py`, swap the CHANNEL_LAYERS to InMemoryChannelLayer (commented out block).

## URL Map
| URL | Description |
|-----|-------------|
| `/` | Landing page |
| `/signup/` `/login/` | Auth |
| `/live/` | **Go Live lobby** — Omegle-style queue |
| `/live/room/<id>/` | Live session chat room |
| `/match/` | Smart match browser |
| `/matches/` | My matches list |
| `/chat/<username>/` | Persistent WS chat |
| `/api/queue-status/` | JSON queue size |
| `/admin/` | Django admin |

## WebSocket Endpoints
| Path | Consumer | Purpose |
|------|----------|---------|
| `ws/queue/` | LiveQueueConsumer | Live matching queue |
| `ws/live/<room_id>/` | LiveChatConsumer | Live session room |
| `ws/chat/<username>/` | MatchChatConsumer | Persistent match chat |

## Smart Matching Engine (core/matching.py)
Weighted similarity with 4 tiers:
- **1.0 Exact** — "Python" == "Python"
- **0.7 Cluster** — "Django" ≈ "Flask" ≈ "Backend" (20+ clusters)
- **0.45 Tag** — "Photography" ≈ "Figma" via shared `visual` tag
- **0.25 Partial** — "Java" ≈ "JavaScript" (substring)

Min threshold: **0.35 in both directions** required for match.
