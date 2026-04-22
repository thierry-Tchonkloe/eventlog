# NOTES

## Technical Decisions

### Framework choice

I chose FastAPI mainly for its strong typing, built-in validation (via Pydantic), and automatic API documentation. These features made it easier to strictly follow the specification (especially for tags, payload validation, and timestamps) while keeping the code clean and maintainable.

FastAPI also allowed me to move faster and stay confident in the correctness of the implementation. While Flask is a solid alternative, I currently have more hands-on experience with FastAPI, which helped me deliver a more reliable result within the time constraints.

---

### Timestamps handling

The specification requires both UTC normalization and preservation of the original format.
To address this, I store:

* a normalized UTC value for filtering and ordering
* the original value for client-facing responses

---

### Duplicate constraint (concurrency)

To safely enforce uniqueness (`user_id`, `occurred_at`), I used a database-level UNIQUE constraint.
This avoids race conditions that could occur with application-level checks.

---

### Pagination strategy

I implemented cursor-based pagination using `(occurred_at, id)` encoded in base64.
This approach is more stable than OFFSET, especially when data changes between requests.

---

### Raw SQL vs ORM

I chose raw SQL for clarity and control. Given the scope of the project and the use of SQLite, it felt more appropriate than adding ORM complexity.

---

## Ambiguities in the spec

* Naive timestamps: I chose to reject them, as they cannot be reliably normalized.
* `event_count`: interpreted as the number of events returned in the current response.
* DELETE behavior: although described as idempotent, the spec requires returning 404 — I followed the described behavior.

---

## Improvements (with more time)

* Database migrations (Alembic)
* Structured logging
* Rate limiting per user
* Load testing under concurrency
* Docker setup for easier deployment

---

**— Thierry Tchonkloe**






# NOTES

## Décisions techniques

### Choix du framework

J’ai choisi FastAPI pour sa gestion native du typage, sa validation via Pydantic et sa documentation automatique.
Cela m’a permis de respecter précisément la spécification (notamment pour les tags, les payloads et les timestamps) tout en gardant un code clair et maintenable.

FastAPI m’a aussi permis d’aller plus vite avec plus de confiance dans le résultat.
Même si Flask reste une très bonne option, j’ai aujourd’hui plus d’expérience pratique avec FastAPI, ce qui m’a aidé à livrer une solution plus fiable dans le temps imparti.

---

### Gestion des timestamps

La spec demande à la fois une normalisation en UTC et la conservation du format original.
J’ai donc choisi de stocker :

* une version normalisée (pour les filtres et le tri)
* une version brute (pour l’affichage côté client)

---

### Contrainte de duplication

Pour garantir l’unicité (`user_id`, `occurred_at`) même en cas de requêtes simultanées, j’ai utilisé une contrainte UNIQUE en base de données.
C’est la solution la plus fiable pour éviter les problèmes de concurrence.

---

### Pagination

J’ai utilisé une pagination par curseur basée sur `(occurred_at, id)` encodé en base64.
C’est plus robuste que OFFSET lorsque les données évoluent entre deux requêtes.

---

### SQL brut vs ORM

J’ai choisi du SQL brut pour garder un contrôle total et une meilleure lisibilité.
Pour un projet de cette taille avec SQLite, cela me semblait plus simple et adapté.

---

## Ambiguïtés dans la spec

* Timestamps sans timezone : rejetés pour éviter toute ambiguïté
* `event_count` : interprété comme le nombre d’éléments retournés
* DELETE : comportement non idempotent → respect de la spec

---

## Améliorations possibles

* Migrations avec Alembic
* Logging structuré
* Rate limiting
* Tests de charge
* Dockerisation

---

**— Thierry Tchonkloe**
