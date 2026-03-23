# Distributed Booking System

An event-driven distributed system project for booking and inventory management, built to practice backend engineering, microservices, caching, and asynchronous workflows.

## Motivation

I built this project to learn distributed systems by designing and implementing a booking platform that can gradually evolve from synchronous service-to-service communication into an event-driven architecture.

Instead of only studying distributed systems theoretically, this project focuses on learning by building.

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
│   ├── gateway/
│   ├── booking-service/
│   ├── inventory-service/
│   ├── payment-service/
│   └── notification-worker/
├── shared/
│   ├── schemas/
│   ├── events/
│   └── utils/
├── infra/
│   ├── postgres/
│   ├── redis/
│   └── kafka/
├── docs/
│   ├── architecture.md
│   ├── api-flow.md
│   └── failure-scenarios.md
└── scripts/
```

## Project Roadmap

### Phase 1
- Booking service
- Inventory service
- PostgreSQL
- Basic synchronous service-to-service communication

### Phase 2
- Redis caching for hot reads
- Kafka-based event streaming
- Notification worker
- Event-driven workflow
- Payment service

### Phase 3
- API gateway
- Frontend dashboard
- Observability
- Retry / dead-letter queue
- Deployment improvements

## Current Status

This project is currently in Phase 2.

Implemented so far:
- Booking Service
- Inventory Service
- PostgreSQL integration
- Docker Compose local multi-container environment
- synchronous service-to-service communication
- inventory reservation before booking creation
- booking validation for positive quantity
- confirmed booking persistence in PostgreSQL
- Redis cache-aside reads for inventory data
- Kafka-based booking event publishing
- Notification Worker for asynchronous event consumption
- notification persistence in PostgreSQL
- Redis-backed idempotent event processing
- immediate retry handling for transient notification failures
- retry-topic republishing for failed notification events
- dead-letter queue support for repeatedly failing events

Current booking flow:
- A client sends a POST /bookings request to Booking Service.
- Booking Service validates the request payload.
- Booking Service synchronously calls Inventory Service to reserve inventory.
- If inventory reservation succeeds, Booking Service stores a confirmed booking in PostgreSQL.
- Booking Service publishes a booking_created event to Kafka.
- Notification Worker consumes the event asynchronously.
- Notification Worker persists a notification record in PostgreSQL.
- Notification Worker marks the event as processed in Redis after successful side effects.


Next steps:
- add tests for key workflows and failure scenarios
- improve observability and structured service logging
- document architecture and failure scenarios more clearly
- introduce Payment Service
- refine status transitions and compensation handling