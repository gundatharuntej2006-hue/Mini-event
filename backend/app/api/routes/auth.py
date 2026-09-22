from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import create_access_token
from app.core.dependencies import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.common import ApiResponse
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import authenticate_user, create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=ApiResponse[Token])
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = create_access_token(subject=user.id, role=user.role.value)
    user_resp = UserResponse.model_validate(user)
    
    return ApiResponse(
        data=Token(
            access_token=token,
            token_type="bearer",
            user=user_resp,
        ),
        message="Authentication successful"
    )


@router.post("/register", response_model=ApiResponse[UserResponse])
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ORGANIZER]))
):
    existing = get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user_in.email}' already exists"
        )
    new_user = create_user(db, user_in)
    return ApiResponse(
        data=UserResponse.model_validate(new_user),
        message="User account created successfully"
    )


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return ApiResponse(
        data=UserResponse.model_validate(current_user),
        message="Current user profile retrieved"
    )
