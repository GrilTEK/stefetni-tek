from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from app.core.auth import (
    create_token,
    ROLES,
    pwd_context,
    set_auth_cookie,
    clear_auth_cookie,
)
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    role: str
    password: str
    identifier: str = ""


class GroupJoinRequest(BaseModel):
    join_code: str
    device_id: str


@router.post("/login")
async def login(req: LoginRequest, response: Response):
    if req.role not in ROLES:
        raise HTTPException(status_code=400, detail="Unknown role")

    if req.role == "photographer":
        from app.core.redis import redis_client

        # Try individual account first
        if redis_client and req.identifier:
            hashed = await redis_client.hget("photographer_accounts", req.identifier)  # type: ignore[misc]
            if hashed:
                stored = hashed if isinstance(hashed, str) else hashed.decode()
                if not pwd_context.verify(req.password, stored):
                    raise HTTPException(status_code=401, detail="Wrong password")
                token_data = {"role": "photographer", "photographer_id": req.identifier}
                token = create_token(token_data, timedelta(days=30))
                set_auth_cookie(response, token, 30 * 24 * 3600)
                return {"access_token": token, "role": "photographer"}

        # Fall back to shared password
        expected_pw = ROLES["photographer"]
        if redis_client:
            stored_pw = await redis_client.get("photographer_password")
            if stored_pw:
                expected_pw = (
                    stored_pw if isinstance(stored_pw, str) else stored_pw.decode()
                )
        if expected_pw != req.password:
            raise HTTPException(status_code=401, detail="Wrong password")

        token_data = {"role": "photographer"}
        if req.identifier:
            token_data["photographer_id"] = req.identifier
        token = create_token(token_data, timedelta(days=30))
        set_auth_cookie(response, token, 30 * 24 * 3600)
        return {"access_token": token, "role": "photographer"}

    # Admin
    expected_pw = ROLES[req.role]
    if expected_pw != req.password:
        raise HTTPException(status_code=401, detail="Wrong password")

    token_data = {"role": req.role}
    expires = timedelta(days=30)
    token = create_token(token_data, expires)
    set_auth_cookie(response, token, 30 * 24 * 3600)
    return {"access_token": token, "role": req.role}


@router.post("/join-group")
async def join_group(req: GroupJoinRequest, response: Response):
    from app.core.database import AsyncSessionLocal
    from app.models.group import Group
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Group).where(
                Group.join_code == req.join_code.upper(), Group.is_active
            )
        )
        group = result.scalar_one_or_none()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found or inactive")

        token = create_token(
            {
                "role": "participant",
                "group_id": group.id,
                "group_number": group.number,
                "device_id": req.device_id,
            },
            timedelta(days=7),
        )

        set_auth_cookie(response, token, 7 * 24 * 3600)
        return {
            "access_token": token,
            "group_id": group.id,
            "group_number": group.number,
            "group_name": group.name,
            "group_color": group.color,
        }


@router.post("/logout")
async def logout(response: Response):
    clear_auth_cookie(response)
    return {"ok": True}
