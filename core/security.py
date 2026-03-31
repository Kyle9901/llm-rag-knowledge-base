from fastapi import Header, HTTPException, status

from core.config import Config


async def verify_bearer_token(authorization: str | None = Header(default=None, alias="Authorization")) -> None:
    """校验 Authorization: Bearer <token>。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少或非法的 Authorization 头。",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.removeprefix("Bearer ").strip()
    if token != Config.API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 校验失败。",
            headers={"WWW-Authenticate": "Bearer"},
        )
