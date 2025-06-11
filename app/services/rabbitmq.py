import aio_pika
from core.config import settings

async def init_rabbitmq():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    orders_queue = await channel.declare_queue("orders", durable=True)
    return connection, channel, orders_queue