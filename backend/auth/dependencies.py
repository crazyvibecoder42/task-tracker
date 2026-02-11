"""
FastAPI dependencies for authentication and authorization.

This module provides dependency functions that can be used in route handlers to:
- Extract and validate current user from JWT tokens or API keys
- Enforce role-based access control (RBAC)
- Provide convenience shortcuts for common permission checks
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth.security import verify_token, verify_api_key

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme for JWT authentication
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """
    Extract and validate the current user from JWT token or API key.

    This dependency supports two authentication methods:
    1. JWT Bearer token in Authorization header
    2. API key in X-API-Key header

    Args:
        credentials: HTTP Bearer credentials (JWT token)
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        User object if authentication succeeds

    Raises:
        HTTPException: 401 if authentication fails

    Example:
        @app.get("/api/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    logger.debug("Attempting to authenticate user")

    # Try JWT authentication first
    if credentials and credentials.credentials:
        logger.debug("Attempting JWT authentication")
        token = credentials.credentials
        payload = verify_token(token)

        if payload is None:
            logger.info("JWT token verification failed")
            # If API key is also provided, try API key fallback instead of failing immediately
            if x_api_key:
                logger.info("JWT failed but X-API-Key present, attempting API key fallback")
            else:
                # No fallback available, raise 401
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            # JWT verification succeeded, continue with JWT flow
            # Check token type
            token_type = payload.get("type")
            if token_type != "access":
                logger.info(f"Invalid token type: {token_type}")
                # Token type validation failure - check for API key fallback
                if x_api_key:
                    logger.info("Invalid token type but X-API-Key present, attempting API key fallback")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token type. Use access token for API requests.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
            else:
                # Token type is valid, extract user_id
                user_id = payload.get("sub")
                if user_id is None:
                    logger.info("Token payload missing 'sub' claim")
                    # Malformed token - check for API key fallback
                    if x_api_key:
                        logger.info("Invalid token payload but X-API-Key present, attempting API key fallback")
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token payload",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
                else:
                    logger.debug(f"JWT authentication successful for user_id: {user_id}")

                    # Parse user_id safely (malformed tokens should return 401, not 500)
                    try:
                        user_id_int = int(user_id)
                    except (TypeError, ValueError):
                        logger.info(f"Invalid user_id format in token: {user_id}")
                        # Malformed user_id - check for API key fallback
                        if x_api_key:
                            logger.info("Invalid user_id format but X-API-Key present, attempting API key fallback")
                        else:
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Invalid token format",
                                headers={"WWW-Authenticate": "Bearer"},
                            )
                    else:
                        # User ID parsed successfully, look up user
                        user = db.query(User).filter(User.id == user_id_int).first()

                        if user is None:
                            logger.info(f"User not found for id: {user_id}")
                            # User not found - check for API key fallback
                            if x_api_key:
                                logger.info("User not found for JWT but X-API-Key present, attempting API key fallback")
                            else:
                                raise HTTPException(
                                    status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="User not found",
                                    headers={"WWW-Authenticate": "Bearer"},
                                )
                        else:
                            # Check if user is active
                            if not getattr(user, "is_active", True):  # Default to True for migrated users
                                logger.info(f"Inactive user attempted access: {user_id}")
                                raise HTTPException(
                                    status_code=status.HTTP_403_FORBIDDEN,
                                    detail="User account is inactive",
                                )

                            # Update last login timestamp
                            user.last_login_at = datetime.utcnow()
                            db.commit()

                            logger.info(f"User authenticated via JWT: {user.email}")
                            return user

    # Try API key authentication
    if x_api_key:
        logger.debug("Attempting API key authentication")
        # Import here to avoid circular dependency
        from models import ApiKey

        # Query all active API keys and check against the provided key
        api_keys = db.query(ApiKey).filter(ApiKey.is_active == True).all()

        for api_key_record in api_keys:
            if verify_api_key(x_api_key, api_key_record.key_hash):
                logger.debug(f"API key matched for user_id: {api_key_record.user_id}")

                # Check expiration
                now = datetime.utcnow().replace(tzinfo=None)  # Make naive for comparison
                expires_at = api_key_record.expires_at.replace(tzinfo=None) if api_key_record.expires_at else None
                if expires_at and expires_at < now:
                    logger.info(f"Expired API key used: {api_key_record.id}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="API key has expired",
                    )

                # Update last used timestamp
                api_key_record.last_used_at = datetime.utcnow()
                db.commit()

                user = db.query(User).filter(User.id == api_key_record.user_id).first()

                if user is None:
                    logger.info(f"User not found for API key: {api_key_record.user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User not found",
                    )

                # Check if user is active
                if not getattr(user, "is_active", True):
                    logger.info(f"Inactive user attempted access via API key: {user.id}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="User account is inactive",
                    )

                logger.info(f"User authenticated via API key: {user.email}")
                return user

        logger.info("API key authentication failed: no matching key found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # No authentication provided
    logger.info("No authentication credentials provided")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(required_role: str):
    """
    Create a dependency that requires a specific user role.

    This is a dependency factory that creates role-checking dependencies.

    Args:
        required_role: Role required to access the endpoint ('admin', 'editor', 'viewer')

    Returns:
        Dependency function that checks user role

    Example:
        @app.delete("/api/admin/users/{id}")
        async def delete_user(
            user_id: int,
            current_user: User = Depends(require_role("admin"))
        ):
            # Only admins can access this endpoint
            pass
    """
    logger.debug(f"Creating role requirement dependency for role: {required_role}")

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        """Check if the current user has the required role."""
        user_role = getattr(current_user, "role", "editor")  # Default to editor for migrated users

        # Role hierarchy: admin > editor > viewer
        role_hierarchy = {"viewer": 0, "editor": 1, "admin": 2}

        current_level = role_hierarchy.get(user_role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        if current_level < required_level:
            logger.info(
                f"Access denied: user {current_user.email} has role '{user_role}', "
                f"but '{required_role}' is required"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {required_role}",
            )

        logger.debug(f"Role check passed for user: {current_user.email}")
        return current_user

    return role_checker


async def get_current_admin(current_user: User = Depends(require_role("admin"))) -> User:
    """
    Convenience dependency for admin-only endpoints.

    This is a shortcut for Depends(require_role("admin")).

    Example:
        @app.get("/api/admin/stats")
        async def admin_stats(admin: User = Depends(get_current_admin)):
            # Only admins can access this
            pass
    """
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.

    This is useful for endpoints that behave differently for authenticated vs anonymous users.

    Args:
        credentials: HTTP Bearer credentials (JWT token)
        x_api_key: API key from X-API-Key header
        db: Database session

    Returns:
        User object if authenticated, None otherwise

    Example:
        @app.get("/api/public/tasks")
        async def list_tasks(user: Optional[User] = Depends(get_optional_user)):
            if user:
                # Show user's private tasks
                pass
            else:
                # Show only public tasks
                pass
    """
    try:
        return await get_current_user(credentials, x_api_key, db)
    except HTTPException:
        logger.debug("Optional user authentication failed, returning None")
        return None
