# Mini Delivery — Architecture & In-Class Demo Guide

## Project Structure

```
app/
├── main.py           # App entry point, router registration
├── database.py       # SQLAlchemy engine + session factory (SQLite)
├── models.py         # ORM models: User, Order, AuditLog
├── auth.py           # JWT creation/verification, bcrypt hashing
├── dependencies.py   # FastAPI dependency injectors (get_db, require_role)
├── audit.py          # Audit log helper (log_action)
├── events.py         # In-memory event bus (publish, subscribe, handlers)
└── routers/
    ├── users.py      # POST /register, POST /login
    ├── orders.py     # POST /orders, POST /orders/{id}/assign,
    │                 # POST /orders/{id}/deliver,
    │                 # GET  /orders/by-h3/{h3}, GET /orders/h3-summary
    └── admin.py      # GET /audit-logs, GET /events
```

---

## Endpoints (9 total)

| Method | Path | Role Required | Description |
|--------|------|--------------|-------------|
| POST | `/register` | — | Create user (customer/courier/admin) |
| POST | `/login` | — | Authenticate, returns JWT |
| POST | `/orders` | customer | Create order; stores H3 index |
| POST | `/orders/{id}/assign` | courier | Courier claims an order |
| POST | `/orders/{id}/deliver` | courier | Mark order as delivered |
| GET | `/orders/by-h3/{h3}` | — | List orders in an H3 cell |
| GET | `/orders/h3-summary` | — | Aggregate counts per H3 cell |
| GET | `/audit-logs` | admin | Filtered audit log |
| GET | `/events` | admin | In-memory event bus log |

---

## Role-Based Access Control (RBAC)

Implemented via `require_role()` in `dependencies.py` — a higher-order FastAPI dependency that:
1. Extracts and decodes the JWT from the `Authorization: Bearer` header
2. Loads the user from the database
3. Compares `user.role` against the required role; raises HTTP 403 if mismatch

**Why this approach?** Clean, DRY — roles are declared at the route level in one line:
```python
user = Depends(require_role("courier"))
```

---

## Event-Driven Architecture

`events.py` implements a publish/subscribe pattern:

- **`publish_event(type, payload)`** — records the event in an in-memory log and dispatches to registered handlers
- **`subscribe(type, handler)`** — registers a callable for an event type
- Three handlers fire automatically: `order_created`, `order_assigned`, `order_delivered`

In production this bus would be replaced by **RabbitMQ** or **Kafka**; the interface (`publish_event` / `subscribe`) would stay identical.

---

## Audit Logging

`log_action(db, user_id, action, detail)` writes to the `audit_logs` table.

Actions logged:

| Action | Triggered by |
|--------|-------------|
| `user_registered` | POST /register |
| `user_login` | POST /login |
| `order_created` | POST /orders |
| `order_assigned` | POST /orders/{id}/assign |
| `order_delivered` | POST /orders/{id}/deliver |

Admins can filter by `action` or `user_id` via query params on `GET /audit-logs`.

---

## H3 Integration

### What is H3?
H3 (by Uber) is a hierarchical hexagonal geospatial indexing system. Every point on Earth maps to a hexagonal cell at each of 16 resolutions. This project uses **resolution 9** (cells ≈ 0.1 km²).

### Why H3 for a delivery domain?

1. **O(1) geographic lookup** — filtering orders by area is a simple string equality check (`WHERE h3_index = ?`) instead of a slow bounding-box or haversine calculation.
2. **Natural clustering** — hexagons have equal distances between all neighbours, unlike square grids. This means a "nearby orders" query is always `k_ring(cell, 1)` — uniform in all directions.
3. **Heat-map / demand aggregation** — `GET /orders/h3-summary` groups by `h3_index` to surface high-demand zones, enabling smarter courier dispatching.
4. **Scalable hierarchy** — you can zoom out to resolution 5 (cities) or in to resolution 11 (individual streets) without changing the schema.

### In this project
- On order creation: `h3.latlng_to_cell(lat, lng, 9)` converts coordinates → cell ID
- Cell ID is stored as a string column in `orders.h3_index` with a DB index
- `GET /orders/by-h3/{h3_index}` — exact cell lookup
- `GET /orders/h3-summary` — aggregation across all cells

---

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI | Async-ready, automatic OpenAPI docs at `/docs`, type-safe dependency injection |
| SQLite | Zero-config for demo/dev; swap to Postgres by changing `DATABASE_URL` only |
| JWT auth | Stateless — no server-side session store needed; scales horizontally |
| In-memory event bus | Demonstrates the pattern without infra dependencies; same interface as a real broker |
| H3 resolution 9 | Balances granularity (0.1 km²) with performance — city-scale deployments stay fast |

---

## Running the Project

```bash
pip install fastapi uvicorn sqlalchemy python-jose passlib[bcrypt] h3
uvicorn app.main:app --reload
```

Interactive docs: http://127.0.0.1:8000/docs

Run the full demo:
```bash
bash demo.sh
```
