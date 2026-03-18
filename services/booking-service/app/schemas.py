# for the use of api input then pack it to model  and response to front-end

from pydantic import BaseModel, Field

class BookingCreate(BaseModel):
    user_id: str
    item_id: str
    # should not be 0
    quantity: int = Field(..., gt=0)


class BookingResponse(BaseModel):
    id: int
    user_id: str
    item_id: str
    quantity: int
    status: str
    # for response 
    class Config:
        from_attributes = True