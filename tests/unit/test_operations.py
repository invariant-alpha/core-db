import pytest
from unittest.mock import AsyncMock, MagicMock

from core_db.operations import DBOperations
from core_db.schemas import DBWriteRequest, DBReadRequest, DBVectorUpsert, DBVectorQuery

@pytest.fixture
def mock_pool():
    pool = MagicMock()
    conn = AsyncMock()
    pool.acquire = AsyncMock(return_value=conn)
    pool.release = AsyncMock()
    return pool, conn

@pytest.mark.asyncio
async def test_write_operation(mock_pool):
    pool, conn = mock_pool
    ops = DBOperations(pool)
    
    req = DBWriteRequest(
        table_name="users",
        data={"id": 1, "name": "test"},
        conflict_action="DO NOTHING"
    )
    
    await ops.write(req)
    
    conn.execute.assert_called_once()
    args, _ = conn.execute.call_args
    assert "INSERT INTO users (id, name)" in args[0]
    assert "$1, $2" in args[0]
    assert "ON CONFLICT DO NOTHING" in args[0]

@pytest.mark.asyncio
async def test_read_operation(mock_pool):
    pool, conn = mock_pool
    # mock fetch returning some dummy records
    conn.fetch.return_value = [{"id": 1, "name": "test"}]
    ops = DBOperations(pool)
    
    req = DBReadRequest(
        table_name="users",
        query_filters={"id": 1}
    )
    
    res = await ops.read(req)
    
    conn.fetch.assert_called_once()
    args, _ = conn.fetch.call_args
    assert "SELECT * FROM users WHERE id = $1" in args[0]
    assert res == [{"id": 1, "name": "test"}]
