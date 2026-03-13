from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
COOKIE_NAME = "st_token"

ROLES = {
    "admin": settings.ADMIN_PASSWORD,
    "photographer": "foto2024",
}


def create_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def set_auth_cookie(response, token: str, max_age: int = 30 * 24 * 3600):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response):
    response.delete_cookie(COOKIE_NAME, path="/")


def require_role(*roles: str):
    async def dependency(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
        token = None
        if credentials:
            token = credentials.credentials
        if not token:
            token = request.cookies.get(COOKIE_NAME)
        if not token:
            raise HTTPException(status_code=401, detail="Authentication required")
        payload = verify_token(token)
        if payload.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return payload
    return dependency


require_admin = require_role("admin")
require_photographer = require_role("admin", "photographer")
