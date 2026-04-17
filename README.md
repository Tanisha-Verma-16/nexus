# Nexus-Flow · Maritime Disruption Intelligence

**Nexus-Flow** is a real‑time maritime risk monitoring and rerouting engine. It simulates a live fleet operating across the trans‑Pacific corridor (Shenzhen → Long Beach), continuously scoring each vessel’s disruption risk based on weather, port congestion, geopolitical factors, and route position. When a critical event (e.g., a simulated storm) is detected, the system generates alternative routes with estimated delays, cost impacts, and carbon deltas – and allows dispatchers to accept a reroute with a single API call.

> ⚓ Built with FastAPI, SQLite, and a lightweight risk‑engine. Includes a live HTML dashboard (WebSocket‑free, REST polling) for fleet visualization.

---

## 📦 Backend Overview

The backend is organized into three core modules:

| Module | Responsibility |
|--------|----------------|
| `shipments.py` | Shipment CRUD, risk analysis endpoint, storm simulation, reroute acceptance |
| `dashboard.py` | Fleet‑wide aggregation (KPI cards, high‑risk lists, bulk analysis) |
| `risk_engine.py` (implied) | Computes disruption scores, generates reroute options, consumes simulated weather/geopolitical data |

All data is persisted in a local SQLite database (`database.db`) with three tables:
- `shipments` – vessel metadata, current waypoint, disruption score, alert state.
- `reroute_suggestions` – generated alternative routes per shipment.
- `disruption_events` – logs of triggered events (storms, critical alerts).

---

## 🚢 Core Features

### 1. Real‑time Risk Scoring
Each shipment has a **disruption score (0–100)** derived from four weighted components:
- **Weather** – forecast wind speed, wave height, precipitation probability.
- **Port congestion** – simulated load at origin/destination/waypoints.
- **Position risk** – deviation from standard route, proximity to hazards.
- **Geopolitical** – maritime security index along the route.

Scores are refreshed on demand via `POST /shipments/{id}/analyze` or in bulk via `POST /dashboard/analyze-all`.

### 2. Storm Simulation (Demo)
The `trigger_storm=true` flag forces a critical weather event for a given shipment:
- Wind speed and wave height are artificially inflated.
- Disruption score jumps above 70 → `alert_active = 1`.
- A `disruption_events` log entry is created.
- Reroute options are generated automatically (see below).

### 3. Intelligent Rerouting
When a shipment’s disruption score ≥ 70, the `generate_reroute_options` function produces alternative routes (e.g., “via Seattle”, “via Panama”) with:
- `estimated_delay_hours`
- `cost_delta_usd` (fuel + operational)
- `carbon_delta_kg`
- `waypoints` (list of `{lon, lat, label}`)

Reroute suggestions are stored in the database and can be accepted via `POST /shipments/{id}/accept-reroute`. Once accepted, the shipment status changes to `rerouting` and its alert is cleared.

### 4. Fleet Dashboard Aggregation
The `/dashboard/summary` endpoint:
- Runs a fresh risk analysis on **all** shipments (or uses cached scores).
- Returns:
  - `fleet_summary` (total / critical / warning / normal counts, average risk, cargo at risk).
  - `high_risk_shipments` (sorted by score).
  - `shipments` with enriched fields (`alert_level`, `alert_message`, `weather_summary`).

This endpoint is designed to be polled every 15–30 seconds by a frontend dashboard.

---

## 🔌 API Endpoints

All endpoints are prefixed with `/api/v1` if mounted accordingly – adjust to your deployment.

### Shipments (`/shipments`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all active shipments with current position and disruption score. |
| `GET` | `/{shipment_id}` | Full details (including full route waypoints). |
| `POST` | `/{shipment_id}/analyze` | Run disruption analysis (optional `?trigger_storm=true`). Returns risk breakdown + reroute options. |
| `POST` | `/{shipment_id}/accept-reroute` | Accept a reroute suggestion (body: `{"route_name": "via Seattle"}`). |
| `GET` | `/{shipment_id}/events` | List all logged disruption events for this shipment. |

### Dashboard (`/dashboard`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/summary` | Fleet‑wide KPI summary + high‑risk list (re‑evaluates risk scores). |
| `GET` | `/analyze-all` | Update `disruption_score` and `alert_active` for every shipment in DB. Useful for cron jobs. |

---

## 🧠 Risk Engine Logic (Conceptual)

The risk engine (`services/risk_engine.py`) implements the following pseudo‑code:

```python
def compute_disruption_score(shipment, override_storm=False):
    weather_risk = compute_weather_risk(shipment['waypoint_index'], override_storm)
    port_risk = compute_port_congestion(shipment['origin'], shipment['destination'])
    position_risk = compute_position_deviation(shipment['waypoint_index'])
    geo_risk = compute_geopolitical_risk(shipment['route'])
    
    total = (weather_risk * 0.4 + port_risk * 0.3 + 
             position_risk * 0.2 + geo_risk * 0.1)
    return {"disruption_score": total, "alert_level": ..., "weather": ...}

def generate_reroute_options(shipment, risk_data):
    # Returns list of dicts with alternative routes, delays, costs.
