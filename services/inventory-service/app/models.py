from sqlalchemy import Column, Integer, String
from .database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(String, unique=True, index=True, nullable=False)
    available_quantity = Column(Integer, nullable=False, default=0)