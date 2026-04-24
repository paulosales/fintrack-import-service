# import-service

A Python/FastAPI microservice that accepts CSV bank-statement uploads from the
frontend, parses them into a normalised JSON format, and publishes the resulting
transactions onto a Kafka topic so the **account-service** can import them into
the database.

---

## Architecture

```
                 ┌──────────────┐
  Browser/FE  ──►  Traefik       │
                 └──────┬───────┘
                        │ POST /import/{bank}
                 ┌──────▼───────────────┐
                 │   import-service      │  (Python / FastAPI)
                 │  - parse CSV          │
                 │  - compute fingerprint│
                 │  - publish to Kafka   │
                 └──────┬───────────────┘
                        │ Kafka topic: transactions-import
                 ┌──────▼───────────────┐
                 │   account-service     │  (Rust / Axum)
                 │  - consume Kafka      │
                 │  - resolve codes      │
                 │  - INSERT IGNORE      │
                 └──────┬───────────────┘
                        │
                 ┌──────▼───────┐
                 │    MySQL      │
                 └──────────────┘
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
| `503`  | Kafka unavailable                      |

---

### `GET /health`

Returns `{"status": "ok"}` — used by Docker / load-balancer health checks.

---

## Kafka message schema

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

| Variable                | Default                  | Description                              |
|-------------------------|--------------------------|------------------------------------------|
| `PORT`                  | `8000`                   | HTTP port to listen on                   |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092`           | Kafka broker address(es)                 |
| `KAFKA_IMPORT_TOPIC`    | `transactions-import`    | Topic name for import messages           |

---

## Development

### Prerequisites

- Python 3.12+
- A running Kafka instance (use `fintrack-dev/docker-compose.yml`)

### Setup

```bash
cd import-service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run locally

```bash
uvicorn main:app --reload --port 8000
```

### Run tests

```bash
pytest --cov=. --cov-report=term-missing
```

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
├── requirements.txt
├── Dockerfile
├── Dockerfile.dev
├── pytest.ini
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
├── kafka/
│   └── producer.py           # confluent-kafka producer
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
