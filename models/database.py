import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = "nexusflow.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS shipments (
            id TEXT PRIMARY KEY,
            vessel_name TEXT NOT NULL,
            cargo TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            carrier TEXT NOT NULL,
            weight_tons REAL NOT NULL,
            waypoint_index INTEGER NOT NULL,
            scheduled_eta TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'in_transit',
            disruption_score REAL DEFAULT 0,
            alert_active INTEGER DEFAULT 0,
            reroute_suggested INTEGER DEFAULT 0,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS disruption_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            description TEXT NOT NULL,
            triggered_at TEXT NOT NULL,
            resolved INTEGER DEFAULT 0,
            FOREIGN KEY (shipment_id) REFERENCES shipments(id)
        );

        CREATE TABLE IF NOT EXISTS weather_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            data TEXT NOT NULL,
            fetched_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reroute_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shipment_id TEXT NOT NULL,
            route_name TEXT NOT NULL,
            route_type TEXT NOT NULL,
            waypoints TEXT NOT NULL,
            estimated_delay_hours REAL,
            cost_delta_usd REAL,
            carbon_delta_kg REAL,
            created_at TEXT NOT NULL,
            accepted INTEGER DEFAULT 0,
            FOREIGN KEY (shipment_id) REFERENCES shipments(id)
        );
    """)

    conn.commit()
    conn.close()


def seed_shipments():
    """Seed initial shipment data if table is empty."""
    from data.shipments import INITIAL_SHIPMENTS

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM shipments")
    count = cur.fetchone()[0]

    if count == 0:
        now = datetime.now(timezone.utc).isoformat()
        for s in INITIAL_SHIPMENTS:
            cur.execute("""
                INSERT INTO shipments
                (id, vessel_name, cargo, origin, destination, carrier, weight_tons,
                 waypoint_index, scheduled_eta, status, disruption_score, alert_active,
                 reroute_suggested, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?)
            """, (
                s["id"], s["vessel_name"], s["cargo"], s["origin"],
                s["destination"], s["carrier"], s["weight_tons"],
                s["waypoint_index"], s["scheduled_eta"], s["status"], now
            ))
        conn.commit()
        print(f"[DB] Seeded {len(INITIAL_SHIPMENTS)} shipments.")

    conn.close()
