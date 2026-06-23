from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import Base, engine
from .routers import consultations
from .routers import occupancy

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartWaiting API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(consultations.router, prefix="/api")
app.include_router(occupancy.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "SmartWaiting API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}
