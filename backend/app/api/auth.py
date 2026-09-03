from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import authenticate_user, create_access_token, get_current_user, permissions_for_role
from app.schemas.common import ApiResponse, LoginRequest, LoginResult, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username or "", payload.password or "")
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        nickname=user.nickname,
    )
    perms = sorted(permissions_for_role(user.role))
    return ApiResponse(
        data=LoginResult(
            access_token=token,
            token_type="bearer",
            user=UserOut(
                id=user.id,
                username=user.username,
                nickname=user.nickname,
                role=user.role,
                permissions=perms,
            ),
        ).model_dump()
    )


@router.get("/me", response_model=ApiResponse)
def me(current=Depends(get_current_user)):
    return ApiResponse(data=UserOut(**current).model_dump())
