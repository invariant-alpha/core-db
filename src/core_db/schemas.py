from typing import Dict, Any, List
from pydantic import BaseModel

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
