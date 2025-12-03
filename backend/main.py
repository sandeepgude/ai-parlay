from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes_bets import router as bets_router
from api.routes_users import router as auth_router
from api.routes_grok import router as grok_router
from api.routes_odds import router as odds_router
from api.routes_ai import router as ai_router
from api.routes_parlay import router as ai_parlay
from database.connection import Base, engine, SessionLocal
# Import models to ensure tables are registered before create_all
import models.team_stats  # noqa: F401
import models.player_stats  # noqa: F401
import models.game  # noqa: F401
import models.team_market  # noqa: F401
import models.player_prop  # noqa: F401
from utils.logger import logger
from services.odds_service import get_odds_data
import asyncio
from dotenv import load_dotenv

app = FastAPI(title="AI Parlay Assistant")

# ✅ Allowed origins (no trailing slash)
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174", 
    "https://your-production-domain.com"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # use your defined list
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
Base.metadata.create_all(bind=engine)
logger.info("✅ Database initialized")


@app.on_event("startup")
async def refresh_odds_background():
    async def _loop():
        while True:
            try:
                db = SessionLocal()
                for sport in ("nba", "nfl"):
                    await get_odds_data(db, sport, force_refresh=True)
            except Exception as e:
                logger.error(f"⚠️ Refresh loop error: {e}")
            finally:
                try:
                    db.close()
                except Exception:
                    pass
            await asyncio.sleep(900)  # ~15 minutes

    asyncio.create_task(_loop())

# Versioned routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(bets_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(grok_router, prefix="/api/v1")
app.include_router(odds_router, prefix="/api/v1")
app.include_router(ai_parlay, prefix="/api/v1")
@app.get("/")
def root():
    logger.info("Health check route called")
    return {"message": "AI Parlay Backend is running"}
