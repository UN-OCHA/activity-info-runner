import pytest
import respx
import httpx
from api.client import ActivityInfoHTTPClient, APIError, AuthenticationError, APITimeoutError

@pytest.mark.asyncio
@respx.mock
async def test_client_request_success():
    client = ActivityInfoHTTPClient("https://api.example.com", api_token="test-token")
    respx.get("https://api.example.com/test").respond(json={"status": "ok"})
    
    response = await client.request("GET", "/test")
    assert response == {"status": "ok"}
    assert respx.calls.last.request.headers["Authorization"] == "Bearer test-token"

@pytest.mark.asyncio
@respx.mock
async def test_client_request_auth_error():
    client = ActivityInfoHTTPClient("https://api.example.com")
    respx.get("https://api.example.com/test").respond(status_code=401)
    
    with pytest.raises(AuthenticationError, match="Invalid API key"):
        await client.request("GET", "/test")

@pytest.mark.asyncio
@respx.mock
async def test_client_request_api_error():
    client = ActivityInfoHTTPClient("https://api.example.com")
    respx.get("https://api.example.com/test").respond(status_code=500, text="Internal Server Error")
    
    with pytest.raises(APIError, match="500: Internal Server Error"):
        await client.request("GET", "/test")

@pytest.mark.asyncio
async def test_client_request_timeout():
    # Use a very short timeout for testing
    timeout = httpx.Timeout(0.001)
    client = ActivityInfoHTTPClient("https://api.example.com", timeout=timeout)
    
    with respx.mock:
        respx.get("https://api.example.com/test").mock(side_effect=httpx.TimeoutException("Timeout"))
        
        # We need to be careful because the client has retries.
        # It will retry 3 times with backoff.
        # To make it fast, we could mock asyncio.sleep or just wait.
        # Actually, let's just mock the side effect to always fail.
        
        with pytest.raises(APITimeoutError):
            await client.request("GET", "/test", retries=1)
