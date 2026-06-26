# Prompt Operativo — CORE_DB

## Ruolo nel Sistema
Infrastruttura di base, Database Manager (Livello 0).
Gestisce il pool di connessioni asincrone a PostgreSQL usando `asyncpg` e le migrazioni dello schema SQL con `Alembic`. Fornisce metodi CRUD tipizzati per il resto del sistema tramite l'Event Bus. Gestisce le operazioni `pgvector` per il RAG (upsert degli embedding, similarity search). Garantisce la persistenza delle configurazioni dei moduli, degli stati di lifecycle e dei task dell'Orchestratore.

## Lifecycle
CORE_IMMUTABLE — Non accetta LifecycleRequest, ma deve restare costantemente in esecuzione per rispondere agli eventi sul bus.

## Configurazione
```python
from pydantic import BaseModel, Field

class DBConfig(BaseModel):
    postgres_dsn: str = Field(default="postgresql://user:pass@localhost:5432/db", description="DSN di connessione a PostgreSQL")
    min_pool_size: int = Field(default=10, description="Dimensione minima pool connessioni")
    max_pool_size: int = Field(default=50, description="Dimensione massima pool connessioni")
```

## Dipendenze
- Moduli già implementati: `core-bus`, `core-vault` (per estrarre il DSN di connessione).
- Moduli simulati dal Mock Module: Nessuno.

## Schema Pydantic Completo
```python
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

class DBWriteRequest(BaseModel):
    table_name: str
    data: Dict[str, Any]
    conflict_action: str = "DO_NOTHING"

class DBReadRequest(BaseModel):
    table_name: str
    query_filters: Dict[str, Any]

class DBVectorUpsert(BaseModel):
    collection_name: str
    vector_id: str
    vector: List[float]
    metadata: Dict[str, Any] = {}

class DBVectorQuery(BaseModel):
    collection_name: str
    query_vector: List[float]
    top_k: int = 5
```

## Contratto Redis Streams
- Stream sottoscritti: `db.write.requested`, `db.read.requested`, `db.vector.upsert`, `db.vector.query` (Consumer Group: `db_manager`)
- Stream pubblicati: `db.write.completed`, `db.read.completed`, `db.vector.results`
- Dead Letter Queue: `system.dlq.events`
- Politica retry: Standard del `core-bus`

## Flusso Principale
1. Boot: Legge il DSN dal Vault. Applica eventuali migrazioni Alembic pendenti (`alembic upgrade head`).
2. Crea il pool di connessioni async (`asyncpg`).
3. Sottoscrive i topic di read/write sul Redis Bus.
4. Quando riceve una richiesta `db.write.requested`, traduce in INSERT/UPDATE sicure, esegue, e pubblica su `db.write.completed`.
5. Quando riceve una richiesta `db.vector.query`, utilizza la distanza cosenoidale in `pgvector` per trovare i top K match e pubblica su `db.vector.results`.

## Struttura Directory
```
core-db/
├── Dockerfile
├── pyproject.toml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
├── docs/
│   └── prompts/
│       └── CORE_DB.md
├── src/
│   └── core_db/
│       ├── __init__.py
│       ├── main.py
│       ├── config.py
│       ├── schemas.py
│       ├── pool.py              # asyncpg connection pool
│       ├── operations.py        # CRUD & Vector ops
│       └── migrations.py        # Wrapper per chiamare alembic programmaticamente
└── tests/
    ├── unit/
    └── integration/
```

## Test Richiesti
- Unit test: Costruzione query SQL a partire dai request payload.
- Integration test con Mock Module: Non usano il mock module, ma test con `pytest-asyncio` su un db effimero (tramite testcontainers o docker-compose) per validare le query `pgvector` e le migrazioni.
- Edge case: Errori di connessione, constraint violation.

## ADR Collegati
Nessuno al momento.

## Definition of Done
- [ ] Tutti i test passano
- [ ] Nessuna chiamata sincrona bloccante (usare asyncpg, alembic supporta modalità async)
- [ ] Nessun segreto nel codice
- [ ] Implementazione pgvector
- [ ] Nessun riferimento ai flussi di business
