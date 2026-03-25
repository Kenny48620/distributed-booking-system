# for the use of database

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from .database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    item_id = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="PENDING")

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, index=True)

    # unique identifier for this event
    event_id = Column(String, unique=True, index=True, nullable=False)
    # what kind of entity this event belongs to
    aggregate_type = Column(String, nullable=False)
    # related entity id, e.g. booking id
    aggregate_id = Column(Integer, nullable=False)
    # event name, e.g. payment_requested
    event_type = Column(String, nullable=False)
    # serialized JSON payload
    payload = Column(Text, nullable=False)
    # PENDING or SENT
    status = Column(String, nullable=False, default="PENDING")
    # when the outbox record was created
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    # when the event was successfully published
    sent_at = Column(DateTime, nullable=True)
