from datetime import datetime, timedelta, timezone
from hmac import compare_digest
from typing import Annotated, Literal

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, ValidationError

from .config import settings


class Principal(BaseModel):
    sub: str = Field(min_length=1, max_length=128)
    department: str = Field(min_length=1, max_length=64)
    role: Literal["employee", "asset_manager", "purchasing", "vendor"]
    vendor_id: str | None = Field(default=None, max_length=64)


bearer = HTTPBearer(auto_error=False)
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
ISSUER = "wonit"
AUDIENCE = "wonit-web"


def get_principal(credentials: Credentials) -> Principal:
    if credentials:
        try:
            claims = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=["HS256"],
                issuer=ISSUER,
                audience=AUDIENCE,
                options={"require": ["exp", "sub"]},
            )
            return Principal.model_validate(claims)
        except (jwt.InvalidTokenError, ValidationError):
            pass
    raise HTTPException(401, "유효한 사용자 토큰이 필요합니다.", headers={"WWW-Authenticate": "Bearer"})


def require_worker(credentials: Credentials) -> None:
    if not credentials or not compare_digest(
        credentials.credentials.encode(), settings.backend_api_token.encode()
    ):
        raise HTTPException(401, "Worker authentication failed")


DemoRole = Literal["asset_manager", "purchasing", "vendor", "employee"]


def create_dev_token(role: DemoRole = "asset_manager") -> str:
    if not settings.dev_mode:
        raise HTTPException(404)
    return jwt.encode(
        {
            "sub": {"asset_manager": "demo-manager", "purchasing": "demo-buyer",
                    "vendor": "demo-vendor", "employee": "demo-employee"}[role],
            "department": "operations",
            "role": role,
            "vendor_id": "sample-vendor" if role == "vendor" else None,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": datetime.now(timezone.utc) + timedelta(hours=2),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
