from sqlalchemy import Column, Integer, String
from database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    booking_id = Column(Integer, nullable=False)
    user_id = Column(String, nullable=False)
    message = Column(String, nullable=False)
    status = Column(String, nullable=False, default="SENT")

    ### addtional functionality may use 

    # channel = Column(String, nullable=False, default="email")
    # message = Column(String, nullable=False)

    # status = Column(String, nullable=False, default="PENDING")
    # retry_count = Column(Integer, nullable=False, default=0)
    # failure_reason = Column(String, nullable=True)