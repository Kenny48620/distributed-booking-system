import requests

INVENTORY_SERVICE_URL = "http://127.0.0.1:8001"


# def check_inventory(item_id: str, quantity: int) -> bool:
#     response = requests.get(f"{INVENTORY_SERVICE_URL}/inventory/{item_id}")

#     if response.status_code != 200:
#         return False

#     data = response.json()
#     return data["available_quantity"] >= quantity


def reserve_inventory(item_id: str, quantity: int) -> bool:
    response = requests.post(
        f"{INVENTORY_SERVICE_URL}/inventory/reserve",
        json={"item_id": item_id, "quantity": quantity},
    )

    return response.status_code == 200