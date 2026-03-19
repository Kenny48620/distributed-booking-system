from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import Inventory
from .schemas import InventorySeed, InventoryResponse, InventoryReserve

from .redis_client import (
    get_cached_inventory,
    set_cached_inventory,
    delete_cached_inventory,
)

router = APIRouter()


# update item quantity of inventory
@router.post("/inventory/seed", response_model=InventoryResponse)
def seed_inventory(payload: InventorySeed, db: Session = Depends(get_db)):
    # find object
    existing = db.query(Inventory).filter(Inventory.item_id == payload.item_id).first()
    # if we have it，update its available quantity
    if existing:
        # update it
        existing.available_quantity = payload.available_quantity
        db.commit()
        db.refresh(existing)

        # update Redis cache too, so cache and DB stay consistent
        set_cached_inventory(
            existing.item_id,
            {
                "id": existing.id,
                "item_id": existing.item_id,
                "available_quantity": existing.available_quantity,
            },
        )

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
    
    # store the newly created inventory data into Redis cache
    set_cached_inventory(
        inventory.item_id,
        {
            "id": inventory.id,
            "item_id": inventory.item_id,
            "available_quantity": inventory.available_quantity,
        },
    )

    return inventory

# return the status of item by item id
@router.get("/inventory/{item_id}", response_model=InventoryResponse)
def get_inventory(item_id: str, db: Session = Depends(get_db)):
    # first try to read inventory from Redis cache
    cached = get_cached_inventory(item_id)
    if cached:
        print(f"cache hit for {item_id}")
        # if cache hit, return cached data directly without querying DB
        return cached
    
    print(f"cache miss for {item_id}")
    # if cache miss, query the database
    inventory = db.query(Inventory).filter(Inventory.item_id == item_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    # convert DB object into a plain dict for caching / returning
    inventory_data = {
        "id": inventory.id,
        "item_id": inventory.item_id,
        "available_quantity": inventory.available_quantity,
    }
    # save DB result into Redis so future reads are faster
    set_cached_inventory(item_id, inventory_data)

    return inventory

# used before booking
@router.post("/inventory/reserve", response_model=InventoryResponse)
def reserve_inventory(payload: InventoryReserve, db: Session = Depends(get_db)):
     # find the inventory record for the requested item
    inventory = db.query(Inventory).filter(Inventory.item_id == payload.item_id).first()
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory not found")
    
    # check if there is enough stock before reserving
    if inventory.available_quantity < payload.quantity:
        raise HTTPException(status_code=400, detail="Insufficient inventory")

    inventory.available_quantity -= payload.quantity
    db.commit()
    # refresh object with latest DB value
    db.refresh(inventory)

    # update Redis cache with the latest remaining quantity
    set_cached_inventory(
        inventory.item_id,
        {
            "id": inventory.id,
            "item_id": inventory.item_id,
            "available_quantity": inventory.available_quantity,
        },
    )

    return inventory