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

This project is currently in Phase 1.

Implemented so far:
- Booking Service
- Inventory Service
- PostgreSQL integration
- Docker Compose local environment
- synchronous service-to-service communication
- inventory reservation before booking creation

Current booking flow:
- Inventory is reserved synchronously through Inventory Service
- A booking is created only after inventory reservation succeeds
- Confirmed bookings are persisted in PostgreSQL

Next steps:
- improve validation and error handling
- add Redis caching
- introduce Kafka for event-driven workflows