# FastCommerce RabbitMQ Order System

A real, local-first RabbitMQ microservices project for learning producer/consumer flows, routing, and event-driven communication.

## Where should you run this project?

Short answer: **run it on your own machine (locally)**.

- ✅ **Local machine (recommended):** fully supported with Docker Desktop (or Docker Engine + Compose plugin).
- ⚠️ **This chat execution environment:** code is created here, but Docker is not available, so the full stack cannot be started here.

So you should clone/copy this repo to your laptop/server and run it locally.

## Architecture

This project has 3 services communicating via RabbitMQ:

1. **Order Service (Producer + API)**
   - Exposes `POST /orders`
   - Publishes `order.created` to `orders.topic`
2. **Payment Service (Consumer + Producer)**
   - Consumes `order.created`
   - Simulates a payment gateway
   - Publishes `payment.success` or `payment.failed` to `payments.topic`
3. **Notification Service (Consumer)**
   - Consumes both `order.created` and `payment.*`
   - Prints simulated email notifications in logs

RabbitMQ Management UI is available for inspection/debugging.

## Tech stack

- Python 3.11
- Flask (Order API)
- pika (RabbitMQ client)
- Docker + Docker Compose

## Prerequisites (local)

1. Install Docker Desktop (Mac/Windows) or Docker Engine (Linux).
2. Verify Docker and Compose are available:

```bash
docker --version
docker compose version
```

## Run locally

### 1) Start everything

```bash
docker compose up --build -d
```

### 2) Check containers

```bash
docker compose ps
```

### 3) Health check API

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

### 4) Create an order

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_email":"alice@example.com","amount":149.99,"currency":"USD"}'
```

### 5) Watch async processing logs

```bash
docker compose logs -f payment-service notification-service
```

You should see:
- payment-service consume `order.created`
- payment-service publish `payment.success` or `payment.failed`
- notification-service emit mock email lines for order + payment events

## RabbitMQ dashboard

- URL: http://localhost:15672
- Username: `guest`
- Password: `guest`

Explore:
- Exchanges: `orders.topic`, `payments.topic`
- Queues: `payment.order.created`, `notification.order.events`, `notification.payment.events`

## Stop everything

```bash
docker compose down
```

## Troubleshooting

- If a service keeps restarting, run:

```bash
docker compose logs -f order-service payment-service notification-service rabbitmq
```

- If port `5672`, `15672`, or `8000` is busy, stop conflicting apps or change mapped ports in `docker-compose.yml`.

## Learning exercises

1. Add retries + dead-letter queue for failed payments.
2. Add a second payment worker to observe work distribution.
3. Route by region/currency with topic keys like `order.created.usd`.
4. Persist events into a database service.
5. Add idempotency checks so duplicate messages are ignored safely.
