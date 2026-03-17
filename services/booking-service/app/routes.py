from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Booking
from .schemas import BookingCreate, BookingResponse


router = APIRouter()

@router.post("/bookings", response_model=BookingResponse)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
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
def get_booking(booking_id: int , db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking