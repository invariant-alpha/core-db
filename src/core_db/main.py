import asyncio
import logging
import os

from core_db.config import DBConfig
from core_db.schemas import DBWriteRequest, DBReadRequest, DBVectorUpsert, DBVectorQuery
from core_db.pool import ConnectionPool
from core_db.operations import DBOperations

try:
    from core_bus.client import RedisBusClient
    from core_bus.schemas import EventEnvelope
except ImportError:
    RedisBusClient = None
    EventEnvelope = None

logger = logging.getLogger(__name__)

async def main():
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting core-db module...")

    if not RedisBusClient:
        logger.error("core_bus is not installed. core-db cannot connect to Redis.")
        return

    config = DBConfig()
    pool = ConnectionPool(config)
    
    # Retry loop to wait for postgres to be ready
    max_retries = 10
    for i in range(max_retries):
        try:
            await pool.init()
            break
        except Exception as e:
            logger.warning(f"Database connection failed, retrying in 2 seconds... ({i+1}/{max_retries}) Error: {e}")
            await asyncio.sleep(2)
    else:
        logger.error("Could not connect to the database after maximum retries.")
        return
    
    ops = DBOperations(pool)
    bus_client = RedisBusClient()
    await bus_client.connect()

    async def on_write(envelope: EventEnvelope):
        req = DBWriteRequest.model_validate(envelope.payload)
        await ops.write(req)
        logger.info(f"DB Write completed for {req.table_name}")

    async def on_read(envelope: EventEnvelope):
        req = DBReadRequest.model_validate(envelope.payload)
        res = await ops.read(req)
        # In a real scenario, this would publish the results back on bus.
        logger.info(f"DB Read completed for {req.table_name}. Found {len(res)} records.")

    async def on_vector_upsert(envelope: EventEnvelope):
        req = DBVectorUpsert.model_validate(envelope.payload)
        await ops.vector_upsert(req)
        logger.info(f"DB Vector Upsert completed for {req.vector_id}")

    async def on_vector_query(envelope: EventEnvelope):
        req = DBVectorQuery.model_validate(envelope.payload)
        res = await ops.vector_query(req)
        logger.info(f"DB Vector Query completed. Found {len(res)} matches.")

    await bus_client.subscribe("db.write.requested", "db_manager", on_write)
    await bus_client.subscribe("db.read.requested", "db_manager", on_read)
    await bus_client.subscribe("db.vector.upsert", "db_manager", on_vector_upsert)
    await bus_client.subscribe("db.vector.query", "db_manager", on_vector_query)
    
    logger.info("core-db module is listening for database requests on bus...")
    
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        logger.info("Shutting down core-db...")
    finally:
        await bus_client.close()
        await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
