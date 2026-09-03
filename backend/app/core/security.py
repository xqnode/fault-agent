from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models import AppUser

bearer_scheme = HTTPBearer(auto_error=False)

# 轻量权限：角色 -> 能力集合（* 表示全开）
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "ADMIN": {"*"},
    "ENGINEER": {
        "dashboard:read",
        "device:read",
        "device:write",
        "alarm:read",
        "alarm:write",
        "simulator:write",
        "analysis:write",
        "work_order:write",
    },
}

# 路径能力映射（前缀匹配，取最长）
PATH_PERMISSIONS: list[tuple[str, str, set[str]]] = [
    # method, path_prefix, required any-of permissions
    ("GET", "/api/dashboard", {"dashboard:read", "*"}),
    ("GET", "/api/devices", {"device:read", "*"}),
    ("POST", "/api/devices", {"device:write", "*"}),
    ("GET", "/api/device-thresholds", {"device:read", "*"}),
    ("POST", "/api/device-thresholds", {"device:write", "*"}),
    ("GET", "/api/alarms", {"alarm:read", "*"}),
    ("POST", "/api/alarms", {"alarm:write", "*"}),
    ("GET", "/api/simulator", {"simulator:write", "*"}),
    ("POST", "/api/simulator", {"simulator:write", "*"}),
    ("POST", "/api/analysis", {"analysis:write", "*"}),
    ("GET", "/api/work-orders", {"work_order:write", "*"}),
    ("POST", "/api/work-orders", {"work_order:write", "*"}),
    ("GET", "/api/fault-records", {"alarm:read", "*"}),
    ("GET", "/api/auth/me", {"dashboard:read", "device:read", "*"}),
]


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 120000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${dk.hex()}"


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        algo, iterations_s, salt, digest = (password_hash or "").split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            (plain or "").encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(dk.hex(), digest)
    except Exception:
        return False


def create_access_token(*, user_id: int, username: str, role: str, nickname: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expire_hours)
    payload: dict[str, Any] = {
        "sub": username,
        "uid": user_id,
        "role": role,
        "nickname": nickname,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或过期的登录凭证",
        ) from exc


def permissions_for_role(role: str) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, set()))


def role_has_permission(role: str, required: Iterable[str]) -> bool:
    owned = permissions_for_role(role)
    if "*" in owned:
        return True
    need = set(required)
    return bool(owned & need)


def resolve_required_permissions(method: str, path: str) -> set[str] | None:
    """Return required permission set for path, or None if no rule (default allow authenticated)."""
    method = method.upper()
    matched: tuple[str, str, set[str]] | None = None
    for m, prefix, perms in PATH_PERMISSIONS:
        if m != method:
            continue
        if path == prefix or path.startswith(prefix.rstrip("/") + "/") or path.startswith(prefix):
            if matched is None or len(prefix) > len(matched[1]):
                matched = (m, prefix, perms)
    return matched[2] if matched else None


def authenticate_user(db: Session, username: str, password: str) -> AppUser:
    user = db.scalar(select(AppUser).where(AppUser.username == username.strip()))
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")
    if user.role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="角色无效")
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录或缺少 Authorization Bearer",
        )
    payload = decode_token(credentials.credentials)
    uid = payload.get("uid")
    username = payload.get("sub")
    if not uid or not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效登录凭证")

    user = db.get(AppUser, int(uid))
    if not user or user.username != username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或凭证失效")
    if user.status != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用")

    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "role": user.role,
        "permissions": sorted(permissions_for_role(user.role)),
    }


# Backward-compatible alias
def get_current_admin(current: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if current.get("role") != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current
