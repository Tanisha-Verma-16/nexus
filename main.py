from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from models.database import init_db, seed_shipments
from routes.shipments import router as shipments_router
from routes.dashboard import router as dashboard_router

app = FastAPI(
    title="Nexus-Flow API",
    description="Predictive logistics disruption engine — Shenzhen → Long Beach lane",
    version="1.0.0",
)

# Allow all origins for the demo — lock this down in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(shipments_router)
app.include_router(dashboard_router)


@app.on_event("startup")
def on_startup():
    print("[Nexus-Flow] Initialising database...")
    init_db()
    seed_shipments()
    print("[Nexus-Flow] Ready. API docs at http://localhost:8000/docs")


@app.get("/")
def root():
    return {
        "service": "Nexus-Flow Predictive Logistics Engine",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "docs": "/docs",
            "shipments": "/shipments",
            "dashboard": "/dashboard/summary",
            "analyze_all": "/dashboard/analyze-all",
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
