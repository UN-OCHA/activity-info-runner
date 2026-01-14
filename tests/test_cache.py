import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel
from api.cache import auto_cache
import api.cache

class DummyModel(BaseModel):
    id: int
    name: str

@pytest.fixture
def mock_cache():
    with patch("api.cache.cache") as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        yield mock

@pytest.mark.asyncio
async def test_auto_cache_miss_simple(mock_cache):
    # Setup
    mock_func = AsyncMock(return_value="result")
    decorated = auto_cache(ttl=60)(mock_func)
    
    # Execute
    res = await decorated("arg1")
    
    # Verify
    assert res == "result"
    mock_func.assert_called_once_with("arg1")
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_called_once()

@pytest.mark.asyncio
async def test_auto_cache_hit_simple(mock_cache):
    # Setup
    mock_cache.get.return_value = "cached_result"
    mock_func = AsyncMock()
    decorated = auto_cache(ttl=60)(mock_func)
    
    # Execute
    res = await decorated("arg1")
    
    # Verify
    assert res == "cached_result"
    mock_func.assert_not_called()

@pytest.mark.asyncio
async def test_auto_cache_hit_model(mock_cache):
    # Setup
    cached_data = {"id": 1, "name": "foo"}
    mock_cache.get.return_value = cached_data
    mock_func = AsyncMock()
    decorated = auto_cache(ttl=60, model=DummyModel)(mock_func)
    
    # Execute
    res = await decorated("arg1")
    
    # Verify
    assert isinstance(res, DummyModel)
    assert res.id == 1
    assert res.name == "foo"

@pytest.mark.asyncio
async def test_auto_cache_miss_model(mock_cache):
    # Setup
    model_instance = DummyModel(id=2, name="bar")
    mock_func = AsyncMock(return_value=model_instance)
    decorated = auto_cache(ttl=60, model=DummyModel)(mock_func)
    
    # Execute
    res = await decorated("arg1")
    
    # Verify
    assert res == model_instance
    # Should cache the dumped model
    mock_cache.set.assert_called_once()
    args, kwargs = mock_cache.set.call_args
    assert args[1] == {"id": 2, "name": "bar"}

@pytest.mark.asyncio
async def test_auto_cache_bypass(mock_cache):
    # Setup
    mock_func = AsyncMock(return_value="result")
    decorated = auto_cache(ttl=60)(mock_func)
    
    # Execute
    res = await decorated("arg1", _bypass_cache=True)
    
    # Verify
    assert res == "result"
    mock_cache.get.assert_not_called()
    mock_cache.set.assert_not_called()
