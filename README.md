# FastCommerce RabbitMQ Order System

A real, local-first RabbitMQ microservices project for learning producer/consumer flows, routing, and event-driven communication.

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

## Run locally

### 1) Start everything

```bash
docker compose up --build -d
```

### 2) Check containers

```bash
docker compose ps
```

### 3) Create an order

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"customer_email":"alice@example.com","amount":149.99,"currency":"USD"}'
```

### 4) Watch async processing logs

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

## Learning exercises

1. Add retries + dead-letter queue for failed payments.
2. Add a second payment worker to observe work distribution.
3. Route by region/currency with topic keys like `order.created.usd`.
4. Persist events into a database service.
5. Add idempotency checks so duplicate messages are ignored safely.
