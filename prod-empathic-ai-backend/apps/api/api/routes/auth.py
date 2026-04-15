from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, Any
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from apps.api.core.config import get_settings
import httpx

settings = get_settings()
CLERK_SECRET_KEY = settings.CLERK_SECRET_KEY
CLERK_AUTHORIZED_PARTY = settings.CLERK_AUTHORIZED_PARTY

router = APIRouter(prefix="/auth", tags=["auth"])

bearer = HTTPBearer(auto_error=False)

def get_clerk_auth(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    if creds is None:
        raise HTTPException(
            status_code=401, 
            detail="No Token Received"
        )

    # Forward all incoming headers, but ensure Authorization is the token you parsed
    headers = dict(request.headers)
    headers["authorization"] = f"Bearer {creds.credentials}"

    # Include cookies too (some setups use them)
    httpx_request = httpx.Request(
        method=request.method,
        url=str(request.url),
        headers=headers,
    )

    sdk = Clerk(bearer_auth=CLERK_SECRET_KEY)

    state = sdk.authenticate_request(
        httpx_request,
        AuthenticateRequestOptions(
            authorized_parties=[CLERK_AUTHORIZED_PARTY],
        ),
    )

    if not state.is_signed_in: 
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized",
        )

    return state.payload

@router.get("/me")
def me(payload=Depends(get_clerk_auth)):
    return {"user_id": payload.get("sub"), "session_id": payload.get("sid")}


