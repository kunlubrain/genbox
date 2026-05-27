from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader
from genbox.core.config import settings

# We'll stick to the X-API-KEY header name but treat it as our Authorization Token
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def get_api_key(token: str = Security(api_key_header)):
    if token in settings.AUTHORIZED_TOKENS:
        return token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid access token",
    )
