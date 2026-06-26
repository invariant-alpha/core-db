import os
from pydantic import BaseModel, Field

class DBConfig(BaseModel):
    postgres_dsn: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/postgres").replace("+asyncpg", ""), 
        description="DSN di connessione a PostgreSQL"
    )
    min_pool_size: int = Field(default=1, description="Dimensione minima pool connessioni")
    max_pool_size: int = Field(default=10, description="Dimensione massima pool connessioni")
