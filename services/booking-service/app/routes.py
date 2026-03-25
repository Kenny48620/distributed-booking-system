import json
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Booking, OutboxEvent
from .schemas import BookingCreate, BookingResponse
# check quantity
from .inventory_client import reserve_inventory

# from .kafka_producer import publish_booking_created_event, publish_payment_request_event
# from .kafka_producer import publish_payment_requested_event


router = APIRouter()

@router.post("/bookings", response_model=BookingResponse)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    # if doesn't have enough quantity, we need to check inventory before doing booking action
    if not reserve_inventory(payload.item_id, payload.quantity):
        raise HTTPException(status_code=400, detail="Booking failed: Insufficient inventory")

    try:

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
        # insert to get booking id
        db.flush()

        # generate a event id for the outbox event
        event_id = str(uuid.uuid4())

        # it will be published to Kafka later
        event_payload = {
            "event_id": event_id,
            "event_type": "payment_requested",
            "booking_id": booking.id,
            "user_id": booking.user_id,
            "item_id": booking.item_id,
            "quantity": booking.quantity,
            "status": booking.status,
        }

        # store event in outbox instead of publishing to Kafka directly
        outbox_event = OutboxEvent(
            event_id=event_id,
            aggregate_type="booking",
            aggregate_id=booking.id,
            event_type="payment_requested",
            payload=json.dumps(event_payload),
            status="PENDING",
        )
        db.add(outbox_event)

        # commit booking + outbox event together
        db.commit()
        db.refresh(booking)

        return booking

    except Exception:
        db.rollback()
        raise

    #     db.commit()
    #     # refresh it from DB so it contains generated fields like id
    #     db.refresh(booking)
    

    # # publish a Kafka event after booking is successfully created
    # # so async consumers notification-worker can listen to this event and process follow-up actions
    # # publish_booking_created_event(booking)
    # publish_payment_requested_event(booking)
    # return booking


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking



