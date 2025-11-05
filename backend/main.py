from fastapi import FastAPI
from api.routes_bets import router as bets_router
from api.routes_users import router as auth_router
from database.connection import Base, engine

app = FastAPI(title="AI Parlay Backend")

Base.metadata.create_all(bind=engine)
app.include_router(bets_router)
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": "AI Parlay Backend is running"}
