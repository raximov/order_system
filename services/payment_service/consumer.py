import json
import os
import random
import time
from datetime import datetime, timezone

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
ORDER_EXCHANGE = os.getenv("ORDER_EXCHANGE", "orders.topic")
PAYMENT_EXCHANGE = os.getenv("PAYMENT_EXCHANGE", "payments.topic")
PAYMENT_QUEUE = os.getenv("PAYMENT_QUEUE", "payment.order.created")


def connect_with_retry(max_retries: int = 20, delay_seconds: int = 3):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=ORDER_EXCHANGE, exchange_type="topic", durable=True)
            channel.exchange_declare(exchange=PAYMENT_EXCHANGE, exchange_type="topic", durable=True)
            channel.queue_declare(queue=PAYMENT_QUEUE, durable=True)
            channel.queue_bind(exchange=ORDER_EXCHANGE, queue=PAYMENT_QUEUE, routing_key="order.created")
            channel.basic_qos(prefetch_count=1)
            return connection, channel
        except Exception as exc:  # pragma: no cover - runtime resiliency
            last_error = exc
            print(f"[payment-service] RabbitMQ not ready (attempt {attempt}/{max_retries}): {exc}")
            time.sleep(delay_seconds)
    raise RuntimeError(f"Could not connect to RabbitMQ: {last_error}")


def process_payment(order: dict) -> dict:
    # Simulate a payment gateway taking time and occasionally failing.
    time.sleep(1.2)
    success = random.random() > 0.15

    return {
        "event_type": "payment.success" if success else "payment.failed",
        "order_id": order["order_id"],
        "customer_email": order["customer_email"],
        "amount": order["amount"],
        "currency": order.get("currency", "USD"),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "reason": None if success else "Card declined by mock gateway",
    }


def main():
    connection, channel = connect_with_retry()

    def callback(ch, method, _properties, body):
        order = json.loads(body)
        print(f"[payment-service] Received order.created order_id={order['order_id']}")

        payment_result = process_payment(order)
        routing_key = payment_result["event_type"]

        ch.basic_publish(
            exchange=PAYMENT_EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(payment_result),
            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
        )

        print(
            f"[payment-service] Published {routing_key} for order_id={order['order_id']}"
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=PAYMENT_QUEUE, on_message_callback=callback)
    print("[payment-service] Waiting for order.created messages...")
    channel.start_consuming()
    connection.close()


if __name__ == "__main__":
    main()
