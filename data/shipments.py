# Realistic waypoints: Shenzhen → Taiwan Strait → Pacific → Long Beach
# Each shipment is at a different stage of the journey

ROUTE_WAYPOINTS = [
    {"lat": 22.5431, "lng": 114.0579, "label": "Shenzhen Port"},
    {"lat": 23.5, "lng": 117.5, "label": "Taiwan Strait"},
    {"lat": 24.5, "lng": 123.0, "label": "East China Sea"},
    {"lat": 26.0, "lng": 135.0, "label": "North Pacific Entry"},
    {"lat": 30.0, "lng": 150.0, "label": "Mid Pacific"},
    {"lat": 34.0, "lng": 165.0, "label": "Pacific Crossing"},
    {"lat": 36.0, "lng": 175.0, "label": "Date Line Approach"},
    {"lat": 37.5, "lng": -175.0, "label": "Date Line Crossed"},
    {"lat": 36.0, "lng": -160.0, "label": "North Pacific"},
    {"lat": 34.5, "lng": -145.0, "label": "Eastern Pacific"},
    {"lat": 33.8, "lng": -130.0, "label": "California Approach"},
    {"lat": 33.75, "lng": -118.19, "label": "Long Beach Port"},
]

# Alternative reroute: via Port of Seattle instead of Long Beach
SEATTLE_REROUTE = [
    {"lat": 36.0, "lng": -160.0, "label": "North Pacific"},
    {"lat": 40.0, "lng": -150.0, "label": "Northern Diversion"},
    {"lat": 44.0, "lng": -135.0, "label": "Oregon Coast Approach"},
    {"lat": 47.6, "lng": -122.3, "label": "Port of Seattle"},
]

# Alternative reroute: via Port of Oakland
OAKLAND_REROUTE = [
    {"lat": 34.5, "lng": -145.0, "label": "Eastern Pacific"},
    {"lat": 34.0, "lng": -135.0, "label": "California Diversion"},
    {"lat": 37.8, "lng": -122.3, "label": "Port of Oakland"},
]

INITIAL_SHIPMENTS = [
    {
        "id": "NF-2841",
        "vessel_name": "MSC Celestino",
        "cargo": "Electronics & Semiconductors",
        "origin": "Shenzhen, CN",
        "destination": "Long Beach, CA",
        "carrier": "MSC",
        "weight_tons": 18400,
        "waypoint_index": 2,  # East China Sea
        "scheduled_eta": "2025-07-18",
        "status": "in_transit",
    },
    {
        "id": "NF-2902",
        "vessel_name": "COSCO Universe",
        "cargo": "Auto Parts & Machinery",
        "origin": "Shenzhen, CN",
        "destination": "Long Beach, CA",
        "carrier": "COSCO",
        "weight_tons": 22100,
        "waypoint_index": 5,  # Pacific Crossing
        "scheduled_eta": "2025-07-14",
        "status": "in_transit",
    },
    {
        "id": "NF-3015",
        "vessel_name": "Evergreen Majesty",
        "cargo": "Consumer Goods & Apparel",
        "origin": "Shenzhen, CN",
        "destination": "Long Beach, CA",
        "carrier": "Evergreen",
        "weight_tons": 15800,
        "waypoint_index": 8,  # North Pacific
        "scheduled_eta": "2025-07-12",
        "status": "in_transit",
    },
    {
        "id": "NF-3087",
        "vessel_name": "ONE Stork",
        "cargo": "Lithium Battery Packs",
        "origin": "Shenzhen, CN",
        "destination": "Long Beach, CA",
        "carrier": "ONE",
        "weight_tons": 9200,
        "waypoint_index": 10,  # California Approach — HIGH RISK position
        "scheduled_eta": "2025-07-10",
        "status": "in_transit",
    },
    {
        "id": "NF-3112",
        "vessel_name": "Yang Ming Witness",
        "cargo": "Medical Equipment",
        "origin": "Shenzhen, CN",
        "destination": "Long Beach, CA",
        "carrier": "Yang Ming",
        "weight_tons": 11600,
        "waypoint_index": 0,  # Just departed Shenzhen
        "scheduled_eta": "2025-07-25",
        "status": "in_transit",
    },
]
