from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Booking
from .schemas import BookingCreate, BookingResponse
# check quantity
from .inventory_client import reserve_inventory

router = APIRouter()

@router.post("/bookings", response_model=BookingResponse)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    # if doesn't have enough quantity, we need to check inventory before doing booking action
    if not reserve_inventory(payload.item_id, payload.quantity):
        raise HTTPException(status_code=400, detail="Booking failed: Insufficient inventory")

    # print("Booking created!")

    # create booking object
    booking = Booking(
        user_id=payload.user_id,
        item_id=payload.item_id,
        quantity=payload.quantity,
        status="PENDING",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return booking


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking