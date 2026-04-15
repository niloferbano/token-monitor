import os

from fastapi import Header, HTTPException


API_KEY = os.getenv("TOKEN_MONITOR_API_KEY", "dev-secret-key")


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_api_key