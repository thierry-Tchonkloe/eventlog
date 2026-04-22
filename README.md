# EventLog API

EventLog is a backend service for storing and querying time-series events.

## Tech Stack:
    Python 3.11+,
    FastAPI,
    SQLite.

## Installation

```bash

git clone https://github.com/thierry-Tchonkloe/eventlog.git
cd eventlog

python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt

```

## Lancement

```bash
uvicorn main:app --reload
```

Documentation interactive : http://localhost:8000/docs

## Tests

```bash
pytest -v

ou/et

pytest --maxfail=1 --disable-warnings -q
```

## Structure

```
eventlog/
│
├── main.py              # Entrée app + lifespan
├── database.py          # Connexion SQLite + schema
├── models.py            # Pydantic (validation + réponses)
├── exceptions.py        # Erreurs métier + handlers HTTP
│
├── routers/
│   ├── events.py        # CRUD /events
│   ├── stats.py         # GET /stats
│   └── debug.py         # POST /debug/echo
│
├── services/
│   ├── event_service.py # Logique métier + pagination curseur
│   └── stats_service.py # Calcul médiane
│
├── tests/
│   ├── conftest.py          # Fixtures : client test, DB in-memory
│   ├── test_events.py       # CRUD + cas limites
│   ├── test_tags.py         # Toute la validation tags
│   ├── test_list.py         # Tests pour la liste des événements
│   ├── test_timestamps.py   # Préservation offset, UTC, alias
│   ├── test_stats.py        # Médiane, edge cases
│   └── test_debug.py        # Echo récursif
│
├── requirements.txt
├── README.md
└── NOTES.md
```

## Endpoints
|------------------------------------------------------------|
| Method | Path             | Description                    |
|--------|------------------|--------------------------------|
| POST   | /events          | Créer un événement             |
| GET    | /events          | Lister avec filtres + curseur  |
| GET    | /events/{id}     | Récupérer un événement         |
| PATCH  | /events/{id}     | Mise à jour partielle          |
| DELETE | /events/{id}     | Supprimer                      |
| GET    | /stats           | Statistiques globales          |
| POST   | /debug/echo      | Echo avec inversion des strings|
| GET    | /health          | Check de santé                 |
|------------------------------------------------------------|


## Notes

=> Timestamps are normalized to UTC but original format is preserved
=> Duplicate events (user_id + occurred_at) are rejected
=> Tags validation strictly follows the specification