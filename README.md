# Token Monitor

`token-monitor` is a FastAPI-based quota gateway that enforces per-tenant token budgets using a sliding-window algorithm.

It is designed as a lightweight prototype of a real AI backend component that sits in front of LLM APIs and prevents cost overruns with low-latency admission checks.

The current implementation is intentionally simple:
- in-memory quota state
- per-tenant token budgets
- sliding-window quota enforcement using a ring-buffer prefix-sum approach
- request deduplication by `request_id`
- FastAPI HTTP endpoints for tenant registration and quota checks

This is a working prototype for quota enforcement logic, not yet a production-ready distributed service.

## What It Does

The service allows you to:
- register a tenant with a token budget and window size
- check whether a request should be admitted
- reject requests with `429 Too Many Requests` when the tenant exceeds its budget
- deduplicate repeated requests so the same `request_id` is not counted twice

## Current Architecture
## Architecture Overview

```text
                ┌──────────────────────┐
                │      Client /        │
                │     AI Agent         │
                └─────────┬────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │   FastAPI Gateway    │
                │  (app/main.py)       │
                └─────────┬────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │     API Layer        │
                │  (core/api.py)       │
                └─────────┬────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │   Service Layer      │
                │ (core/service.py)    │
                │ - tenant lookup      │
                │ - deduplication      │
                │ - admission logic    │
                └─────────┬────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │ Sliding Window State │
                │ (core/quota.py)      │
                │ - ring buffer        │
                │ - running total      │
                │ - check + reserve    │
                └──────────────────────┘

### Core Components

- `app/main.py`
  - creates the FastAPI application
  - mounts the quota router
- `app/core/api.py`
  - exposes the HTTP endpoints
- `app/core/service.py`
  - manages tenant registration, quota checks, and deduplication
- `app/core/quota.py`
  - implements the sliding-window state and token reservation logic
- `app/core/schema.py`
  - defines request and response models

### Quota Model
Internally, each tenant maintains a fixed-size ring buffer of time buckets, allowing constant-time updates and efficient sliding-window aggregation.

Each tenant has:
- `budget_tokens`
- `window_seconds`

For each quota check:
- the service looks up the tenant
- applies the sliding-window calculation
- reserves tokens when the request is allowed
- returns the current usage and remaining budget

Requests are deduplicated by `(tenant_id, request_id)`.

## API Endpoints


```

### `GET /health`

Basic application health endpoint.

Example response:

```json
{
  "status": "ok"
}
```


### `POST /quota/tenants`

Registers a tenant.

Request body:

```json
{
  "tenant_id": "tenant-a",
  "budget_tokens": 10,
  "window_seconds": 60
}
```

Response:

```json
{
  "tenant_id": "tenant-a",
  "budget_tokens": 10,
  "window_seconds": 60
}
```

### `POST /quota/check`

Checks whether a request fits within the tenant budget.

Request body:

```json
{
  "tenant_id": "tenant-a",
  "request_id": "req-1",
  "requested_tokens": 4,
  "now_sec": 100
}
```

Successful response:

```json
{
  "tenant_id": "tenant-a",
  "request_id": "req-1",
  "allowed": true,
  "deduplicated": false,
  "used_tokens": 4,
  "remaining_tokens": 6,
  "budget_tokens": 10,
  "window_seconds": 60,
  "reason": null
}
```

Error responses:
- `404` when the tenant does not exist
- `429` when the token budget is exceeded
- `409` when registering a tenant that already exists

## Local Development

### Requirements

- Python `3.12+`
- Poetry or a compatible environment manager

### Install Dependencies

If you are using Poetry:

```bash
poetry install
```

If you are using the local virtual environment already present in the repo:

```bash
.venv/bin/pip install -e .
```

## Run the Service

Using uvicorn:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Or with Python:

```bash
.venv/bin/python -m app.main
```

The default app address is `http://127.0.0.1:8000`.

## Run Tests

```bash
.venv/bin/pytest -q
```

The current test suite covers:
- tenant registration
- successful quota admission
- budget overflow rejection
- unknown-tenant handling
- duplicate request handling
- sliding-window expiry behavior

## Example Workflow

Register a tenant:

```bash
curl -X POST http://127.0.0.1:8000/quota/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-a",
    "budget_tokens": 10,
    "window_seconds": 60
  }'
```

Check quota:

```bash
curl -X POST http://127.0.0.1:8000/quota/check \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-a",
    "request_id": "req-1",
    "requested_tokens": 4,
    "now_sec": 100
  }'
```

Submit the same request again to observe deduplication:

```bash
curl -X POST http://127.0.0.1:8000/quota/check \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-a",
    "request_id": "req-1",
    "requested_tokens": 4,
    "now_sec": 100
  }'
```

## Performance Characteristics

- O(1) time complexity per quota check using a ring-buffer design
- constant memory per tenant proportional to `window_seconds`
- sub-10ms admission decisions in the hot path (in-memory)

## Limitations

The current code does not yet provide:
- Redis-backed shared state
- persistent storage
- multi-instance coordination
- model-aware pricing or spend tracking in dollars
- reconciliation from immutable event logs
- authentication or authorization
- production-grade observability

Because quota state is stored in memory:
- data is lost on restart
- quotas are local to a single process
- this should not be treated as a distributed quota service yet

## Design Tradeoffs

This prototype prioritizes simplicity and low-latency checks over durability and distribution.

- In-memory state enables fast (<10ms) admission decisions but is not persistent
- Sliding-window aggregation avoids full scans but assumes roughly increasing timestamps
- Deduplication is exact but unbounded in memory (no TTL eviction yet)

In a production system, these tradeoffs would be addressed with Redis-backed state, TTL-based idempotency keys, and distributed coordination.

## Next Steps

The natural next improvements are:
- move quota state to Redis
- replace in-memory deduplication with TTL-backed idempotency keys
- add spend-based enforcement in addition to raw token counts
- add metrics, tracing, and structured error responses
- persist tenant configuration outside process memory
