from fastapi import FastAPI
from .database import Base, engine
from . import models
from .routes import router

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(router)

@app.get("/")
def root():
    return {'message': 'Booking service is running. Please go to /docs or /redoc to check'}

@app.get("/health")
def health():
    return {"status": "ok"}