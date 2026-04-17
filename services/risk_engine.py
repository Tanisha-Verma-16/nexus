"""
Nexus-Flow Disruption Scoring Engine
-------------------------------------
Computes a 0–100 Disruption Probability Score per shipment using:
  - Real-time weather at current waypoint
  - Port congestion model (simulated, realistic values)
  - Cargo sensitivity multipliers
  - Position-based Pacific storm exposure
  - Simulated geopolitical noise

This is intentionally rules-based for the demo. In production this
would be replaced by a trained Vertex AI model.
"""

import random
from datetime import datetime, timezone
from services.weather import fetch_weather
from data.shipments import ROUTE_WAYPOINTS, SEATTLE_REROUTE, OAKLAND_REROUTE

# ── Port Congestion Model ─────────────────────────────────────────────────────
# Simulated but realistic — Long Beach congestion is a known chronic problem.
# In production: pull from Marine Exchange of Southern California API.

def _get_port_congestion(port: str = "long_beach") -> dict:
    """Returns simulated port congestion data."""
    CONGESTION_PROFILES = {
        "long_beach": {
            "queue_depth_vessels": random.randint(18, 34),
            "avg_wait_days": round(random.uniform(3.5, 7.2), 1),
            "congestion_score": random.randint(62, 88),
            "terminal": "TTI Terminal, Pier T",
        },
        "seattle": {
            "queue_depth_vessels": random.randint(3, 9),
            "avg_wait_days": round(random.uniform(0.5, 2.1), 1),
            "congestion_score": random.randint(18, 35),
            "terminal": "Terminal 18, Port of Seattle",
        },
        "oakland": {
            "queue_depth_vessels": random.randint(5, 14),
            "avg_wait_days": round(random.uniform(1.0, 3.5), 1),
            "congestion_score": random.randint(28, 52),
            "terminal": "APMT Oakland",
        },
    }
    return CONGESTION_PROFILES.get(port, CONGESTION_PROFILES["long_beach"])


# ── Cargo Sensitivity Multipliers ────────────────────────────────────────────

CARGO_RISK_MULTIPLIERS = {
    "Electronics & Semiconductors": 1.4,   # moisture sensitive, high value
    "Lithium Battery Packs": 1.5,           # regulatory risk + fire hazard
    "Medical Equipment": 1.6,              # time-critical, compliance risk
    "Auto Parts & Machinery": 1.1,
    "Consumer Goods & Apparel": 0.9,
}

def _cargo_multiplier(cargo: str) -> float:
    for key, mult in CARGO_RISK_MULTIPLIERS.items():
        if key.lower() in cargo.lower():
            return mult
    return 1.0


# ── Main Scoring Function ─────────────────────────────────────────────────────

def compute_disruption_score(shipment: dict, override_storm: bool = False) -> dict:
    """
    Returns a full risk assessment dict for a shipment.
    override_storm=True simulates the "Trigger Storm" demo button.
    """
    waypoint_idx = shipment["waypoint_index"]
    waypoint = ROUTE_WAYPOINTS[min(waypoint_idx, len(ROUTE_WAYPOINTS) - 1)]

    # 1. Fetch real weather at current position
    weather = fetch_weather(waypoint["lat"], waypoint["lng"])

    # 2. Weather risk component (0–40 points)
    wind_kmh = weather["forecast_max_wind_kmh"]
    precip_prob = weather["forecast_max_precip_prob"]
    wave_m = weather["forecast_max_wave_m"]

    if override_storm:
        wind_kmh = max(wind_kmh, 95)
        precip_prob = max(precip_prob, 88)
        wave_m = max(wave_m, 6.5)

    wind_score = min(wind_kmh / 120 * 40, 40)
    precip_score = precip_prob * 0.15
    wave_score = min(wave_m / 10 * 15, 15)
    weather_component = round(wind_score + precip_score + wave_score, 1)

    # 3. Port congestion component (0–30 points)
    congestion = _get_port_congestion("long_beach")
    congestion_component = round(congestion["congestion_score"] * 0.30, 1)

    # 4. Position risk — mid-Pacific is worst (0–15 points)
    # Waypoints 4–7 = peak Pacific exposure
    position_risk_map = {0: 2, 1: 4, 2: 6, 3: 8, 4: 14, 5: 15, 6: 13,
                          7: 11, 8: 8, 9: 6, 10: 4, 11: 1}
    position_component = position_risk_map.get(waypoint_idx, 5)

    # 5. Geopolitical noise (0–10 points) — randomised, simulates news signal
    geo_component = round(random.uniform(2, 10), 1)

    # 6. Raw score
    raw_score = weather_component + congestion_component + position_component + geo_component

    # 7. Apply cargo sensitivity multiplier
    cargo_mult = _cargo_multiplier(shipment.get("cargo", ""))
    final_score = min(round(raw_score * cargo_mult, 1), 100)

    # 8. Determine alert level
    if final_score >= 70:
        alert_level = "critical"
        alert_msg = "High disruption risk — rerouting recommended."
    elif final_score >= 45:
        alert_level = "warning"
        alert_msg = "Moderate risk detected — monitor closely."
    else:
        alert_level = "normal"
        alert_msg = "Route conditions nominal."

    return {
        "disruption_score": final_score,
        "alert_level": alert_level,
        "alert_message": alert_msg,
        "score_breakdown": {
            "weather": weather_component,
            "port_congestion": congestion_component,
            "position_exposure": position_component,
            "geopolitical": geo_component,
            "cargo_multiplier": cargo_mult,
        },
        "weather": weather,
        "port_congestion": congestion,
        "current_waypoint": waypoint,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Reroute Suggestion Generator ─────────────────────────────────────────────

def generate_reroute_options(shipment: dict, risk_data: dict) -> list[dict]:
    """
    Generates 2–3 alternative routing options when disruption score >= 70.
    Returns ranked list with cost/time/carbon trade-offs.
    """
    options = []
    score = risk_data["disruption_score"]

    if score < 70:
        return []

    waypoint_idx = shipment["waypoint_index"]

    # Option A: Seattle Reroute (only viable before waypoint 9)
    if waypoint_idx <= 9:
        options.append({
            "route_name": "Seattle Reroute + Rail to SoCal",
            "route_type": "port_diversion",
            "destination_port": "Port of Seattle",
            "waypoints": SEATTLE_REROUTE,
            "estimated_delay_hours": round(random.uniform(18, 36), 1),
            "cost_delta_usd": round(random.uniform(12000, 28000), 0),
            "carbon_delta_kg": round(random.uniform(-800, 400), 0),
            "demurrage_savings_usd": round(random.uniform(45000, 90000), 0),
            "confidence": 0.87,
            "notes": "Avoids Long Beach congestion. Rail connection pre-available from BNSF Seattle. Net cost positive after demurrage savings.",
            "recommended": True,
        })

    # Option B: Oakland Reroute
    if waypoint_idx <= 10:
        options.append({
            "route_name": "Oakland Port Diversion",
            "route_type": "port_diversion",
            "destination_port": "Port of Oakland",
            "waypoints": OAKLAND_REROUTE,
            "estimated_delay_hours": round(random.uniform(8, 20), 1),
            "cost_delta_usd": round(random.uniform(6000, 15000), 0),
            "carbon_delta_kg": round(random.uniform(-200, 600), 0),
            "demurrage_savings_usd": round(random.uniform(20000, 50000), 0),
            "confidence": 0.79,
            "notes": "Shorter diversion. Congestion moderate at Oakland. Trucking to LA distribution centre adds 6–8 hrs.",
            "recommended": False,
        })

    # Option C: Wait-and-Monitor (always available)
    options.append({
        "route_name": "Hold & Monitor (48hr window)",
        "route_type": "wait_monitor",
        "destination_port": "Long Beach (original)",
        "waypoints": [],
        "estimated_delay_hours": round(random.uniform(36, 72), 1),
        "cost_delta_usd": round(random.uniform(4000, 9000), 0),
        "carbon_delta_kg": 0,
        "demurrage_savings_usd": 0,
        "confidence": 0.55,
        "notes": "Reduced-speed approach to buy time. Riskiest option if storm escalates. Not recommended for time-critical cargo.",
        "recommended": False,
    })

    return options
