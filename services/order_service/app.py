import json
import os
import time
import uuid
from datetime import datetime, timezone

import pika
from flask import Flask, jsonify, request

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
ORDER_EXCHANGE = os.getenv("ORDER_EXCHANGE", "orders.topic")

app = Flask(__name__)


def connect_with_retry(max_retries: int = 20, delay_seconds: int = 3):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=ORDER_EXCHANGE, exchange_type="topic", durable=True)
            return connection, channel
        except Exception as exc:  # pragma: no cover - runtime resiliency
            last_error = exc
            print(f"[order-service] RabbitMQ not ready (attempt {attempt}/{max_retries}): {exc}")
            time.sleep(delay_seconds)
    raise RuntimeError(f"Could not connect to RabbitMQ: {last_error}")


connection, channel = connect_with_retry()


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.post("/orders")
def create_order():
    payload = request.get_json(silent=True) or {}
    customer_email = payload.get("customer_email")
    amount = payload.get("amount")

    if not customer_email or amount is None:
        return jsonify({"error": "customer_email and amount are required"}), 400

    order_event = {
        "event_type": "order.created",
        "order_id": str(uuid.uuid4()),
        "customer_email": customer_email,
        "amount": amount,
        "currency": payload.get("currency", "USD"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    channel.basic_publish(
        exchange=ORDER_EXCHANGE,
        routing_key="order.created",
        body=json.dumps(order_event),
        properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
    )

    print(f"[order-service] Published order.created for order_id={order_event['order_id']}")
    return jsonify({"message": "Order accepted", "order": order_event}), 201


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
