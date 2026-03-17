# for the use of api input then pack it to model  and response to front-end

from pydantic import BaseModel

class BookingCreate(BaseModel):
    user_id: str
    item_id: str
    quantity: int


class BookingResponse(BaseModel):
    id: int
    user_id: str
    item_id: str
    quantity: int
    status: str
    # for response 
    class Config:
        from_attributes = True