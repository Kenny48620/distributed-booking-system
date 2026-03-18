from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Inventory
from .schemas import InventorySeed, InventoryResponse, InventoryReserve

router = APIRouter()


# update item quantity of inventory
@router.post("/inventory/seed", response_model=InventoryResponse)
def seed_inventory(payload: InventorySeed, db: Session = Depends(get_db)):
    # find object
    existing = db.query(Inventory).filter(Inventory.item_id == payload.item_id).first()
    # if we have it
    if existing:
        # update it
        existing.available_quantity = payload.available_quantity
        db.commit()
        db.refresh(existing)
        return existing

    # if we dont' have it, then create the object
    inventory = Inventory(
        item_id=payload.item_id,
        available_quantity=payload.available_quantity,
    )
    # then add it to our db
    db.add(inventory)
    db.commit()
    db.refresh(inventory)
    return inventory

# return the status of item by item id
@router.get("/inventory/{item_id}", response_model=InventoryResponse)
def get_inventory(item_id: str, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.item_id == item_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    return inventory

# used before booking
@router.post("/inventory/reserve", response_model=InventoryResponse)
def reserve_inventory(payload: InventoryReserve, db: Session = Depends(get_db)):
    inventory = db.query(Inventory).filter(Inventory.item_id == payload.item_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")

    if inventory.available_quantity < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient inventory")

    inventory.available_quantity -= payload.quantity
    db.commit()
    db.refresh(inventory)
    return inventory