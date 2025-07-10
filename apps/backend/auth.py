from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes
from jose import jwt, JWTError
from pydantic import BaseModel

from .config import get_settings

settings = get_settings()
ALGORITHM = settings.jwt_algorithm
SECRET_KEY = settings.jwt_secret

oauth2_scheme = HTTPBearer(auto_error=False)


class Actor(BaseModel):
    username: str
    scopes: List[str]


def create_access_token(username: str, scopes: List[str]) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    to_encode = {
        "sub": username,
        "scopes": scopes,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Actor:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )
    return Actor(username=payload["sub"], scopes=payload.get("scopes", []))


async def get_current_actor(
    security_scopes: SecurityScopes,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(oauth2_scheme),
) -> Actor:
    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
        )

    token = creds.credentials
    actor = decode_token(token)

    required = set(security_scopes.scopes)
    if not required.issubset(actor.scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing scopes: {required - set(actor.scopes)}",
        )
    return actor
