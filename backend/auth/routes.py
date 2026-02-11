"""
Authentication API endpoints.

This module provides REST API endpoints for:
- User registration
- Login/logout
- Token refresh with rotation
- API key management
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token,
    generate_api_key,
    hash_api_key,
    COOKIE_SECURE,
    COOKIE_SAMESITE,
    COOKIE_DOMAIN,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from auth.dependencies import get_current_user, get_current_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# Request/Response schemas
class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CreateApiKeyRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Descriptive name for the API key")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="Days until expiration (optional)")


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key: Optional[str] = None  # Only returned on creation
    expires_at: Optional[datetime] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None


class ApiKeyListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user account.

    Args:
        request: Registration data (name, email, password)
        db: Database session

    Returns:
        Created user object

    Raises:
        HTTPException: 400 if email already registered
    """
    logger.info(f"Registration attempt for email: {request.email}")

    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        logger.info(f"Registration failed: email already exists: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Hash password
    logger.debug("Hashing password for new user")
    password_hash = hash_password(request.password)

    # Create new user
    new_user = User(
        name=request.name,
        email=request.email,
    )

    # Set auth fields (using setattr for compatibility with migrated schema)
    setattr(new_user, "password_hash", password_hash)
    setattr(new_user, "role", "editor")  # Default role
    setattr(new_user, "is_active", True)
    setattr(new_user, "email_verified", False)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.critical(f"User registered successfully: {new_user.email} (ID: {new_user.id})")
    return new_user


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Login with email and password.

    Args:
        request: Login credentials
        response: FastAPI response object (to set cookies)
        db: Database session

    Returns:
        Access token for API requests

    Raises:
        HTTPException: 401 if credentials invalid or user inactive

    Note:
        Sets httpOnly refresh token cookie for token rotation
    """
    logger.info(f"Login attempt for email: {request.email}")

    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        logger.info(f"Login failed: user not found: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify password
    password_hash = getattr(user, "password_hash", None)
    if not password_hash:
        logger.info(f"Login failed: user has no password set: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password not set. Please contact administrator.",
        )

    if not verify_password(request.password, password_hash):
        logger.info(f"Login failed: invalid password: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Check if user is active
    if not getattr(user, "is_active", True):
        logger.info(f"Login failed: inactive user: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    # Create tokens
    user_role = getattr(user, "role", "editor")
    token_data = {"sub": str(user.id), "role": user_role, "email": user.email}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Extract JTI from refresh token for tracking
    refresh_payload = verify_token(refresh_token)
    if refresh_payload:
        # Import here to avoid circular dependency
        from models import RefreshToken

        # Store refresh token in database
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_jti=refresh_payload["jti"],
            expires_at=datetime.utcfromtimestamp(refresh_payload["exp"]),
            is_revoked=False,
        )
        db.add(db_refresh_token)

    # Update last login
    setattr(user, "last_login_at", datetime.utcnow())
    db.commit()

    # Set refresh token as httpOnly cookie with environment-aware security settings
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        path="/",  # CRITICAL: Must match path in delete_cookie for logout to work
        httponly=True,
        secure=COOKIE_SECURE,  # True in production (HTTPS only)
        samesite=COOKIE_SAMESITE,  # "strict" in production, "lax" in development
        domain=COOKIE_DOMAIN,  # Explicit domain for subdomain support
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Matches token expiry
    )

    logger.critical(f"User logged in successfully: {user.email} (ID: {user.id})")
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Logout current user and revoke refresh token.

    Args:
        request: FastAPI request object (to read cookies)
        response: FastAPI response object (to clear cookies)
        db: Database session

    Note:
        Clears refresh token cookie and marks token as revoked in database.
        Does not require authentication - works even if access token is missing/expired.
        This ensures users can always logout, even in broken auth states.
    """
    logger.info("Logout request received")

    # Import here to avoid circular dependency
    from models import RefreshToken

    # Read refresh token from cookie
    refresh_token_str = request.cookies.get("refresh_token")

    # If token exists, mark it as revoked in database
    if refresh_token_str:
        payload = verify_token(refresh_token_str)
        if payload:
            token_jti = payload.get("jti")
            if token_jti:
                db_token = db.query(RefreshToken).filter(
                    RefreshToken.token_jti == token_jti
                ).first()
                if db_token:
                    db_token.is_revoked = True
                    db.commit()
                    logger.debug(f"Revoked refresh token with JTI: {token_jti}")

    # Clear refresh token cookie with matching parameters
    # Browser requires matching domain/path/secure/samesite to delete a cookie
    response.delete_cookie(
        key="refresh_token",
        path="/",
        domain=COOKIE_DOMAIN,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE
    )

    logger.critical("User logged out successfully")
    # CRITICAL: Set status code explicitly before returning the mutated response
    # The injected response object doesn't inherit the decorator's status_code
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token from cookie.

    Implements token rotation: old refresh token is revoked and new one is issued.

    Args:
        request: FastAPI request object (to get cookies)
        response: FastAPI response object (to set new cookie)
        db: Database session

    Returns:
        New access token

    Raises:
        HTTPException: 401 if refresh token invalid or revoked
    """
    logger.debug("Token refresh requested")

    # Import here to avoid circular dependency
    from models import RefreshToken

    # Extract refresh token from cookie
    refresh_token_str = request.cookies.get("refresh_token")
    if not refresh_token_str:
        logger.info("Token refresh failed: no refresh token cookie")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
        )

    # Verify refresh token
    payload = verify_token(refresh_token_str)
    if not payload or payload.get("type") != "refresh":
        logger.info("Token refresh failed: invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    # Check if token exists in database (SECURITY: required for revocation)
    token_jti = payload.get("jti")
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token_jti == token_jti
    ).first()

    # SECURITY: Reject tokens not tracked in database (prevents revocation bypass)
    if not db_token:
        logger.info(f"Token refresh failed: token not found in database (JTI: {token_jti})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found or has been revoked",
        )

    # Check if token is revoked
    if db_token.is_revoked:
        logger.info(f"Token refresh failed: token revoked (JTI: {token_jti})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    # Get user (parse sub safely to avoid 500 on malformed tokens)
    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        logger.info(f"Invalid sub format in refresh token: {payload.get('sub')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not getattr(user, "is_active", True):
        logger.info(f"Token refresh failed: user not found or inactive (ID: {user_id})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old refresh token (token rotation)
    db_token.is_revoked = True

    # Create new tokens
    user_role = getattr(user, "role", "editor")
    token_data = {"sub": str(user.id), "role": user_role, "email": user.email}

    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token({"sub": str(user.id)})

    # Store new refresh token in database
    new_refresh_payload = verify_token(new_refresh_token)
    if new_refresh_payload:
        db_refresh_token = RefreshToken(
            user_id=user.id,
            token_jti=new_refresh_payload["jti"],
            expires_at=datetime.utcfromtimestamp(new_refresh_payload["exp"]),
            is_revoked=False,
        )
        db.add(db_refresh_token)

    db.commit()

    # Set new refresh token cookie with environment-aware security settings
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        path="/",  # CRITICAL: Must match path in delete_cookie for logout to work
        httponly=True,
        secure=COOKIE_SECURE,  # True in production (HTTPS only)
        samesite=COOKIE_SAMESITE,  # "strict" in production, "lax" in development
        domain=COOKIE_DOMAIN,  # Explicit domain for subdomain support
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Matches token expiry
    )

    logger.critical(f"Token refreshed successfully for user: {user.email} (ID: {user.id})")
    return {"access_token": new_access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Args:
        current_user: Authenticated user from dependency

    Returns:
        Current user object
    """
    logger.debug(f"Fetching user info for: {current_user.email}")
    return current_user


@router.post("/api-keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a new API key for the current user.

    Args:
        request: API key creation parameters
        current_user: Authenticated user
        db: Database session

    Returns:
        API key object with the raw key (only shown once)

    Note:
        The raw API key is only returned once during creation.
        Store it securely - it cannot be retrieved again.
    """
    logger.info(f"Creating API key for user: {current_user.email}, name: {request.name}")

    # Import here to avoid circular dependency
    from models import ApiKey

    # Generate API key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)

    # Calculate expiration if specified
    expires_at = None
    if request.expires_days:
        expires_at = datetime.utcnow() + timedelta(days=request.expires_days)

    # Create API key record
    api_key = ApiKey(
        user_id=current_user.id,
        key_hash=key_hash,
        name=request.name,
        expires_at=expires_at,
        is_active=True,
    )

    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    logger.critical(f"API key created: {request.name} for user {current_user.email} (ID: {api_key.id})")

    # Return response with raw key (only time it's shown)
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,  # Only returned on creation
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
    )


@router.get("/api-keys", response_model=list[ApiKeyListResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all API keys for the current user.

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of API keys (without raw keys)
    """
    logger.debug(f"Listing API keys for user: {current_user.email}")

    # Import here to avoid circular dependency
    from models import ApiKey

    api_keys = db.query(ApiKey).filter(ApiKey.user_id == current_user.id).all()

    logger.debug(f"Found {len(api_keys)} API keys for user {current_user.email}")
    return api_keys


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke (deactivate) an API key.

    Args:
        key_id: ID of the API key to revoke
        current_user: Authenticated user
        db: Database session

    Raises:
        HTTPException: 404 if key not found or doesn't belong to user
    """
    logger.info(f"Revoking API key {key_id} for user: {current_user.email}")

    # Import here to avoid circular dependency
    from models import ApiKey

    api_key = db.query(ApiKey).filter(
        ApiKey.id == key_id, ApiKey.user_id == current_user.id
    ).first()

    if not api_key:
        logger.info(f"API key not found or unauthorized: {key_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    # Deactivate the key
    api_key.is_active = False
    db.commit()

    logger.critical(f"API key revoked: {api_key.name} (ID: {key_id}) for user {current_user.email}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
