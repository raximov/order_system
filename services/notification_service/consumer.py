import json
import os
import time

import pika

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/%2F")
ORDER_EXCHANGE = os.getenv("ORDER_EXCHANGE", "orders.topic")
PAYMENT_EXCHANGE = os.getenv("PAYMENT_EXCHANGE", "payments.topic")
NOTIFICATION_ORDER_QUEUE = os.getenv("NOTIFICATION_ORDER_QUEUE", "notification.order.events")
NOTIFICATION_PAYMENT_QUEUE = os.getenv("NOTIFICATION_PAYMENT_QUEUE", "notification.payment.events")


def connect_with_retry(max_retries: int = 20, delay_seconds: int = 3):
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            params = pika.URLParameters(RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange=ORDER_EXCHANGE, exchange_type="topic", durable=True)
            channel.exchange_declare(exchange=PAYMENT_EXCHANGE, exchange_type="topic", durable=True)

            channel.queue_declare(queue=NOTIFICATION_ORDER_QUEUE, durable=True)
            channel.queue_bind(exchange=ORDER_EXCHANGE, queue=NOTIFICATION_ORDER_QUEUE, routing_key="order.created")

            channel.queue_declare(queue=NOTIFICATION_PAYMENT_QUEUE, durable=True)
            channel.queue_bind(exchange=PAYMENT_EXCHANGE, queue=NOTIFICATION_PAYMENT_QUEUE, routing_key="payment.*")

            return connection, channel
        except Exception as exc:  # pragma: no cover - runtime resiliency
            last_error = exc
            print(f"[notification-service] RabbitMQ not ready (attempt {attempt}/{max_retries}): {exc}")
            time.sleep(delay_seconds)
    raise RuntimeError(f"Could not connect to RabbitMQ: {last_error}")


def main():
    connection, channel = connect_with_retry()

    def on_order_created(ch, method, _properties, body):
        event = json.loads(body)
        print(
            "[notification-service] EMAIL => "
            f"To: {event['customer_email']} | Subject: Order received | Order ID: {event['order_id']}"
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def on_payment_event(ch, method, _properties, body):
        event = json.loads(body)
        subject = "Payment successful" if event["event_type"] == "payment.success" else "Payment failed"
        print(
            "[notification-service] EMAIL => "
            f"To: {event['customer_email']} | Subject: {subject} | Order ID: {event['order_id']}"
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=NOTIFICATION_ORDER_QUEUE, on_message_callback=on_order_created)
    channel.basic_consume(queue=NOTIFICATION_PAYMENT_QUEUE, on_message_callback=on_payment_event)
    print("[notification-service] Waiting for order/payment events...")
    channel.start_consuming()
    connection.close()


if __name__ == "__main__":
    main()
