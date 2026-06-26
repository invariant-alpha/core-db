import json
from typing import List, Dict, Any, Optional
from .pool import ConnectionPool
from .schemas import DBWriteRequest, DBReadRequest, DBVectorUpsert, DBVectorQuery

class DBOperations:
    def __init__(self, pool: ConnectionPool):
        self.pool = pool

    async def write(self, request: DBWriteRequest) -> None:
        """Esegue una query INSERT o UPDATE a partire dalla richiesta."""
        conn = await self.pool.acquire()
        try:
            columns = list(request.data.keys())
            values = list(request.data.values())
            
            placeholders = ", ".join(f"${i+1}" for i in range(len(values)))
            cols_str = ", ".join(columns)
            
            query = f"INSERT INTO {request.table_name} ({cols_str}) VALUES ({placeholders})"
            if request.conflict_action != "DO_NOTHING":
                query += f" ON CONFLICT {request.conflict_action}"
                
            await conn.execute(query, *values)
        finally:
            await self.pool.release(conn)

    async def read(self, request: DBReadRequest) -> List[Dict[str, Any]]:
        """Esegue una SELECT con i filtri forniti."""
        conn = await self.pool.acquire()
        try:
            query = f"SELECT * FROM {request.table_name}"
            values = []
            
            if request.query_filters:
                conditions = []
                for i, (k, v) in enumerate(request.query_filters.items()):
                    conditions.append(f"{k} = ${i+1}")
                    values.append(v)
                query += " WHERE " + " AND ".join(conditions)
                
            records = await conn.fetch(query, *values)
            return [dict(r) for r in records]
        finally:
            await self.pool.release(conn)

    async def vector_upsert(self, request: DBVectorUpsert) -> None:
        """Inserisce o aggiorna un embedding in pgvector."""
        conn = await self.pool.acquire()
        try:
            # Assuming table has columns: id, vector (vector), metadata (jsonb)
            query = f"""
                INSERT INTO {request.collection_name} (id, vector, metadata)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE SET 
                    vector = EXCLUDED.vector,
                    metadata = EXCLUDED.metadata
            """
            await conn.execute(
                query, 
                request.vector_id, 
                request.vector, 
                json.dumps(request.metadata)
            )
        finally:
            await self.pool.release(conn)

    async def vector_query(self, request: DBVectorQuery) -> List[Dict[str, Any]]:
        """Ricerca di similarità tramite pgvector (cosine distance <=>)."""
        conn = await self.pool.acquire()
        try:
            # Querying using cosine distance
            query = f"""
                SELECT id, metadata, vector <=> $1 AS distance
                FROM {request.collection_name}
                ORDER BY vector <=> $1
                LIMIT $2
            """
            records = await conn.fetch(query, request.query_vector, request.top_k)
            return [dict(r) for r in records]
        finally:
            await self.pool.release(conn)
