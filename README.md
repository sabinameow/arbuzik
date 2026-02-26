# Arbuzik — Mini Delivery API

A learning-oriented REST service demonstrating key backend patterns: role-based access control (RBAC), event-driven architecture, H3 geospatial indexing, and audit logging. Built with **FastAPI** + **SQLAlchemy**, using SQLite as the database.

---
Group members:
230103040 - Muratbaikyzy Sabina
230103315 - Kelsingazine Adeliya


## Quick Start

```bash
pip install fastapi uvicorn sqlalchemy python-jose passlib[bcrypt] h3
uvicorn app.main:app --reload
```

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Run the full demo script:
```bash
bash demo.sh
```

---

## Project Structure

```
app/
├── main.py           # Entry point, router registration
├── database.py       # SQLAlchemy engine + session factory (SQLite)
├── models.py         # ORM models: User, Order, AuditLog
├── schemas.py        # Pydantic request schemas
├── auth.py           # JWT creation/verification, bcrypt password hashing
├── dependencies.py   # FastAPI dependencies: get_db, require_role
├── audit.py          # Audit log helper: log_action
├── events.py         # In-memory event bus (publish/subscribe)
└── routers/
    ├── users.py      # POST /register, POST /login
    ├── orders.py     # Order creation and lifecycle management
    └── admin.py      # GET /audit-logs, GET /events
```

---

## Endpoints

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/register` | — | Register a user (customer / courier / admin) |
| POST | `/login` | — | Authenticate and receive a JWT |
| POST | `/orders` | customer | Create an order; coordinates are converted to an H3 index |
| POST | `/orders/{id}/assign` | courier | Courier claims an order |
| POST | `/orders/{id}/deliver` | courier | Courier marks an order as delivered |
| GET | `/orders/by-h3/{h3}` | — | List all orders in an H3 cell |
| GET | `/orders/h3-summary` | — | Aggregate order counts per H3 cell |
| GET | `/audit-logs` | admin | Audit log with filtering by action and user_id |
| GET | `/events` | admin | In-memory event bus log |

---

## Role-Based Access Control (RBAC)

Implemented via the `require_role()` dependency in `dependencies.py`:
1. Extracts and decodes the JWT from the `Authorization: Bearer` header.
2. Loads the user from the database.
3. Compares `user.role` against the required role; returns HTTP 403 on mismatch.

```python
user = Depends(require_role("courier"))
```

Three roles are supported: `customer`, `courier`, `admin`.

---

## Event-Driven Architecture

`events.py` implements a publish/subscribe pattern:

- `publish_event(type, payload)` — records the event in an in-memory log and dispatches it to all registered handlers.
- `subscribe(type, handler)` — registers a handler for a given event type.

Three events fire automatically: `order_created`, `order_assigned`, `order_delivered`.

> In production, this bus would be replaced by **RabbitMQ** or **Kafka** with no changes to the interface.

---

## Audit Logging

`log_action(db, user_id, action, detail)` writes a record to the `audit_logs` table.

| Action | Triggered by |
|--------|-------------|
| `user_registered` | POST /register |
| `user_login` | POST /login |
| `order_created` | POST /orders |
| `order_assigned` | POST /orders/{id}/assign |
| `order_delivered` | POST /orders/{id}/deliver |

Admins can filter logs by `action` or `user_id` via query parameters.

---

## H3 Geospatial Indexing

**H3** (by Uber) is a hierarchical hexagonal geospatial indexing system.

This project uses **resolution 9** (cell ≈ 0.1 km²):

- On order creation, coordinates are converted via `h3.latlng_to_cell(lat, lng, 9)` into a cell ID.
- The cell ID is stored in `orders.h3_index` with a database index.
- `GET /orders/by-h3/{h3_index}` — O(1) area lookup instead of slow bounding-box or haversine queries.
- `GET /orders/h3-summary` — demand heatmap for smarter courier dispatching.

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI | Async-ready, automatic OpenAPI docs at `/docs`, type-safe dependency injection |
| SQLite | Zero-config for development; switch to Postgres by changing `DATABASE_URL` only |
| JWT | Stateless auth — no server-side session store; scales horizontally |
| In-memory event bus | Demonstrates the pattern without infrastructure dependencies |
| H3 resolution 9 | Balances granularity (0.1 km²) with query performance at city scale |

---

## Data Models

**User** — `id`, `username`, `password` (bcrypt), `role`

**Order** — `id`, `status` (created → assigned → delivered), `latitude`, `longitude`, `h3_index`, `customer_id`, `courier_id`, `created_at`

**AuditLog** — `id`, `action`, `user_id`, `detail`, `timestamp`
