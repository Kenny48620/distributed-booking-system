from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import Base, engine
from . import models
from .routes import router
from .payment_consumer import start_payment_result_consumer

Base.metadata.create_all(bind=engine)


# has been deprecated
# @app.on_event("startup")
# def startup_event():
#     start_payment_result_consumer()
# so use FastAPI recommend way to create a thread
@asynccontextmanager
async def lifespan(app: FastAPI):

    # start up
    print("Booking Service is starting up...", flush=True)
    # start the background Kafka consumer at application startup
    start_payment_result_consumer()

    # hand control back to FastAPI so it can start serving requests
    yield
    # shutdown
    print("Booking Service is shutting down...", flush=True)
    # put shutdown cleanup here later if needed
    


app = FastAPI(lifespan=lifespan)
app.include_router(router)

@app.get("/")
def root():
    return {'message': 'Booking service is running. Please go to /docs or /redoc to check'}

@app.get("/health")
def health():
    return {"status": "ok"}


# @app.on_event("startup")
# def startup_event():
#     start_payment_result_consumer()