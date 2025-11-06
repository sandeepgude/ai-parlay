from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes_bets import router as bets_router
from api.routes_users import router as auth_router
from database.connection import Base, engine
from utils.logger import logger

app = FastAPI(title="AI Parlay Assistant")

# Allow React and production domains
origins = [
    "http://localhost:3000",
    "https://your-production-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
Base.metadata.create_all(bind=engine)
logger.info("Database initialized")

# Versioned routes
app.include_router(auth_router, prefix="/api/v1")
app.include_router(bets_router, prefix="/api/v1")

@app.get("/")
def root():
    logger.info("Health check route called")
    return {"message": "AI Parlay Backend is running"}
