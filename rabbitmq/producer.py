import json
import os
import uuid
from typing import Any

import aio_pika

from utils.logger import get_logger

logger = get_logger("rabbitmq.producer")

RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq:5672/")
RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "transactions-import")


async def publish_import_batch(
    importer_type: str,
    transactions: list[dict[str, Any]],
) -> str:
    """Publish a batch of parsed transactions to the RabbitMQ import queue.

    Returns the import_id assigned to this batch.
    """
    import_id = str(uuid.uuid4())
    payload = {
        "import_id": import_id,
        "importer": importer_type,
        "transactions": transactions,
    }
    message_body = json.dumps(payload, default=str).encode("utf-8")

    connection = await aio_pika.connect_robust(RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        await channel.declare_queue(RABBITMQ_QUEUE, durable=True)
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=message_body,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=RABBITMQ_QUEUE,
        )
        logger.info(
            "Published import batch %s to queue '%s'", import_id, RABBITMQ_QUEUE
        )

    return import_id
