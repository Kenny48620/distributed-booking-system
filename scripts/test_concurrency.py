import threading
import requests
"""
    This script tests concurrency protection during booking.

    It sends multiple booking requests at the same time for the same inventory item
    to verify that row locking prevents race conditions and overselling.

    Before running this script, seed the inventory first:

    curl -X POST http://127.0.0.1:8001/inventory/seed \
        -H "Content-Type: application/json" \
        -d '{"item_id":"ticket_concurrent","available_quantity":3}'
"""
URL = "http://127.0.0.1:8000/bookings"

payloads = [
    {"user_id": f"u{i}", "item_id": "ticket_concurrent", "quantity": 1}
    for i in range(1, 11)
]

success_count = 0
fail_count = 0
lock = threading.Lock()

def send_request(payload):
    global success_count, fail_count
    try:
        response = requests.post(URL, json=payload, timeout=5)
        print(payload["user_id"], response.status_code, response.text)

        with lock:
            if response.status_code == 200:
                success_count += 1
            else:
                fail_count += 1
    except Exception as e:
        print(payload["user_id"], "ERROR", str(e))
        with lock:
            fail_count += 1

threads = []
for payload in payloads:
    t = threading.Thread(target=send_request, args=(payload,))
    threads.append(t)
    t.start()

for t in threads:
    t.join()

print(f"\nSuccess: {success_count}")
print(f"Fail: {fail_count}")