from pydantic import BaseModel


class InventorySeed(BaseModel):
    item_id: str
    available_quantity: int


class InventoryResponse(BaseModel):
    id: int
    item_id: str
    available_quantity: int

    class Config:
        from_attributes = True