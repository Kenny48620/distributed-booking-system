from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Booking
from .schemas import BookingCreate, BookingResponse
# check quantity
from .inventory_client import reserve_inventory

# from .kafka_producer import publish_booking_created_event, publish_payment_request_event
from .kafka_producer import publish_payment_requested_event


router = APIRouter()

@router.post("/bookings", response_model=BookingResponse)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    # if doesn't have enough quantity, we need to check inventory before doing booking action
    if not reserve_inventory(payload.item_id, payload.quantity):
        raise HTTPException(status_code=400, detail="Booking failed: Insufficient inventory")

    # print("Booking created!")

    # create new booking record in booking-service DB
    booking = Booking(
        user_id=payload.user_id,
        item_id=payload.item_id,
        quantity=payload.quantity,
        # set to PENDING because inventory reservation already succeeded
        status="PENDING",
    )
    # add it to current DB session
    db.add(booking)
    db.commit()
    # refresh it from DB so it contains generated fields like id
    db.refresh(booking)
    

    # publish a Kafka event after booking is successfully created
    # so async consumers notification-worker can listen to this event and process follow-up actions
    # publish_booking_created_event(booking)
    publish_payment_requested_event(booking)
    return booking


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking