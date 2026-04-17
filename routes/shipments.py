from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import json

from models.database import get_db
from services.risk_engine import compute_disruption_score, generate_reroute_options
from data.shipments import ROUTE_WAYPOINTS

router = APIRouter(prefix="/shipments", tags=["Shipments"])


@router.get("/")
def list_shipments():
    """Get all active shipments with their current positions and risk scores."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shipments ORDER BY disruption_score DESC")
    rows = cur.fetchall()
    conn.close()

    shipments = []
    for row in rows:
        s = dict(row)
        wp_idx = min(s["waypoint_index"], len(ROUTE_WAYPOINTS) - 1)
        s["current_position"] = ROUTE_WAYPOINTS[wp_idx]
        s["route_progress_pct"] = round(wp_idx / (len(ROUTE_WAYPOINTS) - 1) * 100, 1)
        shipments.append(s)

    return {"shipments": shipments, "total": len(shipments)}


@router.get("/{shipment_id}")
def get_shipment(shipment_id: str):
    """Get full detail for a single shipment."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    s = dict(row)
    wp_idx = min(s["waypoint_index"], len(ROUTE_WAYPOINTS) - 1)
    s["current_position"] = ROUTE_WAYPOINTS[wp_idx]
    s["route_waypoints"] = ROUTE_WAYPOINTS
    s["route_progress_pct"] = round(wp_idx / (len(ROUTE_WAYPOINTS) - 1) * 100, 1)
    return s


@router.post("/{shipment_id}/analyze")
def analyze_shipment(shipment_id: str, trigger_storm: bool = False):
    """
    Run full disruption analysis on a shipment.
    trigger_storm=true simulates the demo "storm event" button.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shipments WHERE id = ?", (shipment_id,))
    row = cur.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Shipment {shipment_id} not found")

    shipment = dict(row)
    risk_data = compute_disruption_score(shipment, override_storm=trigger_storm)
    score = risk_data["disruption_score"]
    alert_active = 1 if score >= 70 else 0
    reroute_suggested = 0

    reroute_options = []
    if alert_active:
        reroute_options = generate_reroute_options(shipment, risk_data)
        reroute_suggested = 1

        # Persist reroute suggestions
        for opt in reroute_options:
            cur.execute("""
                INSERT INTO reroute_suggestions
                (shipment_id, route_name, route_type, waypoints,
                 estimated_delay_hours, cost_delta_usd, carbon_delta_kg, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                shipment_id,
                opt["route_name"],
                opt["route_type"],
                json.dumps(opt["waypoints"]),
                opt["estimated_delay_hours"],
                opt["cost_delta_usd"],
                opt["carbon_delta_kg"],
                datetime.now(timezone.utc).isoformat(),
            ))

        # Log disruption event if storm was triggered
        if trigger_storm:
            cur.execute("""
                INSERT INTO disruption_events
                (shipment_id, event_type, severity, description, triggered_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                shipment_id,
                "weather_storm",
                "critical",
                f"Simulated storm event: wind {risk_data['weather']['forecast_max_wind_kmh']:.0f}km/h, "
                f"waves {risk_data['weather']['forecast_max_wave_m']:.1f}m",
                datetime.now(timezone.utc).isoformat(),
            ))

    # Update shipment risk score in DB
    cur.execute("""
        UPDATE shipments
        SET disruption_score = ?, alert_active = ?, reroute_suggested = ?, updated_at = ?
        WHERE id = ?
    """, (score, alert_active, reroute_suggested, datetime.now(timezone.utc).isoformat(), shipment_id))

    conn.commit()
    conn.close()

    return {
        "shipment_id": shipment_id,
        "vessel_name": shipment["vessel_name"],
        **risk_data,
        "reroute_options": reroute_options,
    }


@router.post("/{shipment_id}/accept-reroute")
def accept_reroute(shipment_id: str, route_name: str):
    """Mark a reroute suggestion as accepted — simulates dispatcher approval."""
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE reroute_suggestions SET accepted = 1
        WHERE shipment_id = ? AND route_name = ?
    """, (shipment_id, route_name))

    cur.execute("""
        UPDATE shipments SET status = 'rerouting', alert_active = 0, updated_at = ?
        WHERE id = ?
    """, (datetime.now(timezone.utc).isoformat(), shipment_id))

    conn.commit()
    conn.close()

    return {
        "message": f"Reroute accepted for {shipment_id}",
        "route": route_name,
        "status": "rerouting",
    }


@router.get("/{shipment_id}/events")
def get_disruption_events(shipment_id: str):
    """Get all disruption events logged for a shipment."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM disruption_events
        WHERE shipment_id = ? ORDER BY triggered_at DESC
    """, (shipment_id,))
    rows = cur.fetchall()
    conn.close()
    return {"events": [dict(r) for r in rows]}
