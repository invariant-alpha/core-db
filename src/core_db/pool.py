import asyncpg
import logging
from typing import Optional
from .config import DBConfig
from pgvector.asyncpg import register_vector

logger = logging.getLogger(__name__)

class ConnectionPool:
    def __init__(self, config: DBConfig):
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None

    async def init(self):
        async def init_connection(conn):
            await register_vector(conn)
            
        self._pool = await asyncpg.create_pool(
            dsn=self.config.postgres_dsn,
            min_size=self.config.min_pool_size,
            max_size=self.config.max_pool_size,
            init=init_connection
        )
        logger.info(f"Database connection pool created (min: {self.config.min_pool_size}, max: {self.config.max_pool_size})")

    async def close(self):
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")

    async def acquire(self) -> asyncpg.Connection:
        if not self._pool:
            raise RuntimeError("Connection pool not initialized")
        return await self._pool.acquire()

    async def release(self, conn: asyncpg.Connection):
        if self._pool:
            await self._pool.release(conn)
