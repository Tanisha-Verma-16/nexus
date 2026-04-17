from fastapi import APIRouter
from models.database import get_db
from services.risk_engine import compute_disruption_score, generate_reroute_options
from data.shipments import ROUTE_WAYPOINTS

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary")
def get_dashboard_summary():
    """
    Fleet-wide summary — the main data feed for the dashboard header cards.
    Runs a fresh risk analysis on all shipments and returns aggregated stats.
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shipments")
    rows = cur.fetchall()
    conn.close()

    shipments_data = []
    critical_count = 0
    warning_count = 0
    normal_count = 0
    total_score = 0
    high_risk_shipments = []

    for row in rows:
        s = dict(row)
        risk = compute_disruption_score(s)
        score = risk["disruption_score"]
        level = risk["alert_level"]
        total_score += score

        wp_idx = min(s["waypoint_index"], len(ROUTE_WAYPOINTS) - 1)
        s["current_position"] = ROUTE_WAYPOINTS[wp_idx]
        s["disruption_score"] = score
        s["alert_level"] = level
        s["alert_message"] = risk["alert_message"]
        s["weather_summary"] = {
            "wind_kmh": risk["weather"]["forecast_max_wind_kmh"],
            "precip_prob": risk["weather"]["forecast_max_precip_prob"],
            "wave_m": risk["weather"]["forecast_max_wave_m"],
        }

        if level == "critical":
            critical_count += 1
            high_risk_shipments.append({
                "id": s["id"],
                "vessel_name": s["vessel_name"],
                "score": score,
                "cargo": s["cargo"],
                "position": ROUTE_WAYPOINTS[wp_idx]["label"],
            })
        elif level == "warning":
            warning_count += 1
        else:
            normal_count += 1

        shipments_data.append(s)

    avg_fleet_risk = round(total_score / max(len(shipments_data), 1), 1)

    # Estimate total cargo at risk (shipments with score >= 45)
    at_risk_weight = sum(
        s["weight_tons"] for s in shipments_data
        if s["disruption_score"] >= 45
    )

    return {
        "fleet_summary": {
            "total_shipments": len(shipments_data),
            "critical": critical_count,
            "warning": warning_count,
            "normal": normal_count,
            "avg_fleet_risk_score": avg_fleet_risk,
            "cargo_at_risk_tons": at_risk_weight,
        },
        "high_risk_shipments": sorted(high_risk_shipments, key=lambda x: -x["score"]),
        "shipments": sorted(shipments_data, key=lambda x: -x["disruption_score"]),
    }


@router.get("/analyze-all")
def analyze_all_shipments():
    """
    Run disruption scoring on every shipment and update the DB.
    Call this periodically (e.g., every 15 min via a cron job).
    """
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM shipments")
    rows = cur.fetchall()
    conn.close()

    from datetime import datetime, timezone
    results = []

    conn = get_db()
    cur = conn.cursor()

    for row in rows:
        s = dict(row)
        risk = compute_disruption_score(s)
        score = risk["disruption_score"]
        alert_active = 1 if score >= 70 else 0

        cur.execute("""
            UPDATE shipments
            SET disruption_score = ?, alert_active = ?, updated_at = ?
            WHERE id = ?
        """, (score, alert_active, datetime.now(timezone.utc).isoformat(), s["id"]))

        results.append({
            "id": s["id"],
            "vessel": s["vessel_name"],
            "score": score,
            "level": risk["alert_level"],
        })

    conn.commit()
    conn.close()

    return {"updated": len(results), "results": results}
