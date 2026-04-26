# import-service

A Python/FastAPI microservice that accepts CSV bank-statement uploads from the
frontend, parses them into a normalised JSON format, and publishes the resulting
transactions onto a RabbitMQ queue so the **account-service** can import them
into the database.

---

## Architecture

```
                 ┌──────────-────┐
  Browser/FE  ──►| Traefik       │
                 └──────┬────-───┘
                        │ POST /import/{bank}
                 ┌──────▼──────────-─────┐
                 │   import-service      │  (Python / FastAPI)
                 │  - parse CSV          │
                 │  - compute fingerprint│
                 │  - publish to Kafka   │
                 └──────┬───────────-────┘
                        │ RabbitMQ queue: transactions-import
                 ┌──────▼────────────-───┐
                 │   account-service     │  (Rust / Axum)
                 │  - consume RabbitMQ   │
                 │  - resolve codes      │
                 │  - INSERT IGNORE      │
                 └──────┬─────────────-──┘
                        │
                 ┌──────▼──────-─┐
                 │    MySQL      │
                 └──────────────-┘
```

---

## Supported importers

| Importer key   | Bank / Account                    |
|----------------|-----------------------------------|
| `pcfinancial`  | PC Financial (credit card)        |
| `mbna`         | MBNA (credit card)                |
| `rbc`          | RBC (chequing / savings / Visa)   |
| `bb`           | Banco do Brasil (conta corrente)  |
| `nu`           | Nubank (credit card)              |
| `cibic-checking` | CIBC Chequing                   |
| `cibic-savings`  | CIBC Savings                    |
| `c6-checking`  | C6 Bank (conta corrente)          |

---

## REST API

### `POST /api/v1/import/{importer_type}`

Upload a CSV file and enqueue its transactions for import.

**Path parameter**

| Name            | Description                                        |
|-----------------|----------------------------------------------------|
| `importer_type` | One of the importer keys listed in the table above |

**Request**

`Content-Type: multipart/form-data`

| Field  | Type | Description            |
|--------|------|------------------------|
| `file` | file | The CSV file to import |

**Headers**

| Header          | Value                        |
|-----------------|------------------------------|
| `Authorization` | `Bearer <keycloak_jwt_token>` |

**Response `200 OK`**

```json
{
  "import_id":    "550e8400-e29b-41d4-a716-446655440000",
  "importer":     "pcfinancial",
  "queued_count": 42,
  "message":      "Transactions queued for import successfully"
}
```

**Error responses**

| Status | Condition                              |
|--------|----------------------------------------|
| `400`  | Unknown importer or empty file         |
| `401`  | Missing `Authorization` header         |
| `415`  | Unsupported file content-type          |
| `422`  | CSV could not be parsed                |
| `503`  | RabbitMQ unavailable                   |

---

### `GET /health`

Returns `{"status": "ok"}` — used by Docker / load-balancer health checks.

---

## RabbitMQ message schema

```json
{
  "import_id":    "550e8400-e29b-41d4-a716-446655440000",
  "importer":     "pcfinancial",
  "transactions": [
    {
      "account_code":           "PCFINANCIAL",
      "datetime":               "2024-01-15 12:00:00",
      "amount":                 -50.25,
      "description":            "GROCERY STORE",
      "transaction_type_code":  "PURCHASE",
      "fingerprint":            "d5a44a049ac7a65abf8e0b8c7be96d30"
    }
  ]
}
```

The `fingerprint` is an MD5 hash of `datetime|amount|description`. The
account-service uses `INSERT IGNORE` on this field to guarantee idempotency.

---

## Configuration

All settings are read from environment variables (`.env` supported via
`python-dotenv`).

| Variable                    | Default                       | Description                              |
|-----------------------------|-------------------------------|------------------------------------------|
| `PORT`                      | `3002`                        | HTTP port to listen on                   |
| `RABBITMQ_URL`              | `amqp://guest:guest@localhost` | RabbitMQ connection URL                  |
| `RABBITMQ_IMPORT_QUEUE`     | `transactions-import`         | Queue name for import messages           |

---

## Development

### Prerequisites

- [uv](https://docs.astral.sh/uv/) — Python package manager
- Python 3.12+ (uv will install it automatically if needed)
- A running RabbitMQ instance (use `fintrack-dev/docker-compose.yml`)

### Setup

```bash
cd import-service
uv sync
```

`uv sync` creates a virtual environment in `.venv/` and installs all
dependencies (including dev) from `uv.lock`.

### Run locally

```bash
uv run uvicorn main:app --reload --port 3002
```

### Run tests

```bash
uv run pytest --cov=. --cov-report=term-missing
```

### Format code

[Ruff](https://docs.astral.sh/ruff/) is used as the formatter (Black-compatible, 88-char lines).

```bash
# Format all files in-place
uv run ruff format .

# Preview what would change without writing
uv run ruff format --check .
```

### Lint

Ruff also handles linting (pyflakes, pycodestyle, isort, pyupgrade rules).

```bash
# Check for lint errors
uv run ruff check .

# Auto-fix fixable issues
uv run ruff check --fix .
```

### Add / remove dependencies

```bash
# Add a runtime dependency
uv add <package>

# Add a dev-only dependency
uv add --dev <package>

# Remove a dependency
uv remove <package>
```

After any change `uv.lock` is updated automatically.

---

## Docker

```bash
# Production
docker build -t import-service .

# Development (hot-reload)
docker build -f Dockerfile.dev -t import-service:dev .
```

---

## Project structure

```
import-service/
├── main.py                   # FastAPI application entry point
├── pyproject.toml            # Project metadata and dependencies
├── uv.lock                   # Locked dependency graph
├── Dockerfile
├── Dockerfile.dev
├── core/
│   ├── importer.py           # Abstract base class for all importers
│   └── fingerprint.py        # MD5 fingerprint generation
├── importers/
│   ├── pcfinancial.py
│   ├── mbna.py
│   ├── rbc.py
│   ├── bb.py
│   ├── nu.py
│   ├── cibic_checking.py
│   ├── cibic_savings.py
│   └── c6_checking.py
├── rabbitmq/
│   └── producer.py           # aio-pika RabbitMQ producer
├── routers/
│   └── import_router.py      # FastAPI router with the upload endpoint
├── utils/
│   ├── date_utils.py
│   └── logger.py
└── tests/
    ├── conftest.py
    ├── test_importers.py
    ├── test_import_router.py
    └── test_fingerprint.py
```
