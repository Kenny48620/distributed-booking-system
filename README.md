# Distributed Booking System

An event-driven distributed systems project for booking and inventory management, built to practice backend engineering, concurrency control, asynchronous workflows, and reliability patterns.

## Motivation

I built this project to learn distributed systems by designing and implementing a booking platform that evolves from synchronous service-to-service communication into a more reliable event-driven architecture.

Rather than only studying distributed systems theoretically, this project focuses on learning by building and exploring real-world challenges such as overselling prevention, dual-write consistency, retries, idempotency, and failure recovery.

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- Redis
- Kafka
- Docker Compose

## Project Structure

```text
distributed-booking-system/
├── README.md
├── .gitignore
├── docker-compose.yml
├── services/
│   ├── booking-service/
│   ├── inventory-service/
│   ├── payment-service/
│   └── notification-worker/
├── shared/
├── infra/
├── docs/
└── scripts/
```

## Current Status

This project is currently in Phase 2.

### Implemented so far

- Booking, Inventory, and Payment services, plus a Notification Worker
- PostgreSQL persistence for booking and notification data
- Docker Compose local multi-container development environment
- Synchronous inventory reservation before booking creation
- Redis cache-aside reads for inventory data
- Kafka-based asynchronous event publishing and consumption
- Booking lifecycle transitions: `PENDING` → `CONFIRMED` / `FAILED`
- Reserved inventory release on payment failure
- Redis-backed idempotent event processing
- Retry-topic and dead-letter queue handling for failed events
- Row-level locking for inventory reservation to prevent overselling
- Outbox Pattern for reliable event publication from Booking Service

## Current Booking Flow

1. A client sends a `POST /bookings` request to Booking Service.
2. Booking Service validates the request payload and calls Inventory Service to reserve inventory.
3. If reservation succeeds, Booking Service stores the booking in PostgreSQL with status `PENDING`.
4. In the same database transaction, Booking Service stores a `payment_requested` outbox event.
5. A background outbox publisher reads pending outbox events and publishes them to Kafka.
6. Payment Service consumes `payment_requested` and simulates either payment success or payment failure.
7. Payment Service publishes either `payment_succeeded` or `payment_failed`.
8. Booking Service consumes the payment result asynchronously and updates the booking to `CONFIRMED` or `FAILED`.
9. If payment fails, Booking Service also releases the reserved inventory.

## Reliability and Consistency Patterns

This project explores several common distributed systems reliability patterns:

- **Row-level locking** to prevent overselling under concurrent booking requests
- **Inventory reservation** before confirmation to protect shared stock
- **Outbox Pattern** to reduce dual-write inconsistency between the database and Kafka
- **Idempotent consumers** to safely handle duplicate event delivery
- **Retry handling** for transient failures
- **Dead-letter queue (DLQ)** for repeatedly failing events

## Concurrency Protection Test

To validate oversell prevention, I sent **10 concurrent booking requests** for the same item while the available inventory quantity was set to **3**.

### Result

- **3 requests succeeded**
- **7 requests failed** with `Insufficient inventory`

This verifies that the inventory reservation flow, combined with row-level locking, prevents overselling under concurrent booking attempts.

## Quick Start

### Prerequisites

Make sure you have the following installed:

- Docker
- Docker Compose

### 1. Clone the repository

```bash
git clone git@github.com:Kenny48620/distributed-booking-system.git
cd distributed-booking-system
```

### 2. Start all services

```bash
docker compose up -d --build
```

This starts the core services, including:

- Booking Service
- Inventory Service
- Payment Service
- Notification Worker
- PostgreSQL
- Redis
- Kafka

### 3. Kafka topic initialization

Topics are automatically initialized by the kafka-init service.
(Wait a few seconds for containers to be ready before verifying).

You can verify the topics with:

```bash
docker exec -it booking-kafka kafka-topics.sh --list --bootstrap-server localhost:9092
```

### 4. Seed inventory

```bash
curl -X POST http://127.0.0.1:8001/inventory/seed \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "ticket_1",
    "available_quantity": 3
  }'
```

### 5. Create a booking

```bash
curl -X POST http://127.0.0.1:8000/bookings \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u1000",
    "item_id": "ticket_1",
    "quantity": 1
  }'
```

A successful request initially creates the booking with status `PENDING`, then the booking is updated asynchronously after payment processing.

### 6. Check booking status

```bash
curl http://127.0.0.1:8000/bookings/1
```

Depending on the payment result, the booking will eventually become:

- `CONFIRMED`
- `FAILED`

### 7. Explore APIs

After starting the services locally, you can explore the API documentation through FastAPI's Swagger UI:

- **Booking Service:** http://127.0.0.1:8000/docs
- **Inventory Service:** http://127.0.0.1:8001/docs

## Future Improvements

- Add automated tests for critical workflows and failure scenarios
- Improve structured logging and observability across services
- Expand failure scenario documentation
- Strengthen end-to-end verification for retry and DLQ behavior
- Improve outbox publisher retry and monitoring
- Add an API Gateway for unified external access

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.