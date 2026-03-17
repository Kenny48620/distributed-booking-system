# for the use of database

from sqlalchemy import Column, Integer, String
from .database import Base


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    item_id = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String, nullable=False, default="PENDING")