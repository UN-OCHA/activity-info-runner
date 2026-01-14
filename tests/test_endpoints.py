import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from api.endpoints import ActivityInfoEndpoints, ActivityInfoHTTPClient, APIError
from api.models import DatabaseTree, FormSchema, OperationCalculationFormulasField, FormElement

@pytest.fixture
def mock_http_client():
    client = MagicMock(spec=ActivityInfoHTTPClient)
    client.request = AsyncMock()
    return client

@pytest.fixture
def endpoints(mock_http_client):
    return ActivityInfoEndpoints(mock_http_client)

@pytest.fixture
def mock_cache():
    # Patch the cache object in api.cache to ensure it's a miss
    with patch("api.cache.cache") as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        yield mock

@pytest.mark.asyncio
async def test_get_database_tree(endpoints, mock_http_client, mock_cache):
    # Setup
    mock_data = {
        "databaseId": "db1",
        "userId": "user1",
        "version": "v1",
        "label": "My DB",
        "description": "Desc",
        "ownerRef": {"id": "o1", "name": "Owner", "email": "owner@example.com"},
        "billingAccountId": 123,
        "language": "en",
        "originalLanguage": "en",
        "role": {"id": "r1", "parameters": {}, "resources": []},
        "suspended": False,
        "billingPlan": "free",
        "storage": "cloud",
        "publishedTemplate": False,
        "resources": [],
        "grants": [],
        "roles": [],
        "securityCategories": []
    }
    mock_http_client.request.return_value = mock_data

    # Execute
    result = await endpoints.get_database_tree("db1")

    # Verify
    assert isinstance(result, DatabaseTree)
    assert result.databaseId == "db1"
    mock_http_client.request.assert_called_once_with("GET", "/databases/db1")

@pytest.mark.asyncio
async def test_get_database_tree_validation_error(endpoints, mock_http_client, mock_cache):
    mock_http_client.request.return_value = {"invalid": "data"}
    
    with pytest.raises(APIError, match="Response does not match DatabaseTree schema"):
        await endpoints.get_database_tree("db1")

@pytest.mark.asyncio
async def test_get_form(endpoints, mock_http_client, mock_cache):
    mock_data = [{"id": "r1", "data": "value"}]
    mock_http_client.request.return_value = mock_data

    result = await endpoints.get_form("form1")
    
    assert result == mock_data
    mock_http_client.request.assert_called_once_with("GET", "/form/form1/query")

@pytest.mark.asyncio
async def test_get_form_schema(endpoints, mock_http_client, mock_cache):
    mock_data = {
        "id": "form1",
        "schemaVersion": 1,
        "databaseId": "db1",
        "label": "Form 1",
        "elements": []
    }
    mock_http_client.request.return_value = mock_data

    result = await endpoints.get_form_schema("form1")
    
    assert isinstance(result, FormSchema)
    assert result.id == "form1"
    mock_http_client.request.assert_called_once_with("GET", "/form/form1/schema")

@pytest.mark.asyncio
async def test_get_operation_calculation_formulas_fields(endpoints, mock_http_client, mock_cache):
    # This method calls get_form with _bypass_cache=True internally
    mock_data = [
        {
            "@id": "f1",
            "@lastEditTime": 123,
            "REFORDER": 1,
            "DESC": "desc",
            "APPLY": "Internal",
            "SYSPREFIX": "P",
            "SYSFIELD": "F",
            "FILTER": "true",
            "FORMULA": "1"
        }
    ]
    # We need to mock what get_form returns.
    # Since get_operation_calculation_formulas_fields calls get_form,
    # and get_form calls self._http.request, we just mock the request.
    
    mock_http_client.request.return_value = mock_data
    
    result = await endpoints.get_operation_calculation_formulas_fields("form1")
    
    assert len(result) == 1
    assert isinstance(result[0], OperationCalculationFormulasField)
    assert result[0].id == "f1"
    
    # Note: get_operation_calculation_formulas_fields calls get_form, which calls request.
    mock_http_client.request.assert_called_once_with("GET", "/form/form1/query")

@pytest.mark.asyncio
async def test_get_operation_calculation_formulas_fields_error(endpoints, mock_http_client, mock_cache):
    mock_http_client.request.return_value = [{"invalid": "data"}]
    
    with pytest.raises(APIError, match="Form does not match CostIndicator schema"):
        await endpoints.get_operation_calculation_formulas_fields("form1")
