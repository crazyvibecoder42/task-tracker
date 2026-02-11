"""
Security utilities for password hashing, JWT token management, and API key handling.

This module provides cryptographic functions for:
- Password hashing using Argon2id (memory-hard, GPU-resistant)
- JWT access and refresh token creation and verification
- API key generation and hashing
"""

import logging
import secrets
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

logger = logging.getLogger(__name__)


def is_production_like() -> bool:
    """
    Check if the current environment is production-like (production or staging).

    Returns:
        True if ENVIRONMENT is "production" or "staging", False otherwise

    Note:
        This is used for security-sensitive checks like JWT secret validation,
        HTTPS requirements, and secure cookie settings.
    """
    env = os.environ.get("ENVIRONMENT", "development").lower()
    return env in ("production", "staging")


# Password hashing configuration using Argon2id
# Argon2id is recommended for password hashing as it's memory-hard and GPU-resistant
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT configuration
# Load SECRET_KEY from environment variable (REQUIRED for security)
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    # For local development only - generate a random key
    # CRITICAL: In production, this MUST be set via environment variable
    if is_production_like():
        raise ValueError(
            "JWT_SECRET_KEY environment variable is required in production. "
            "Generate a secure key with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    else:
        # Development fallback with warning
        SECRET_KEY = "dev-insecure-key-" + secrets.token_urlsafe(32)
        logger.warning(
            "⚠️  JWT_SECRET_KEY not set! Using temporary development key. "
            "This is INSECURE for production. Set JWT_SECRET_KEY environment variable."
        )

# JWT configuration - read from environment with safe defaults
ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

# Parse token expiry times from environment with validation
try:
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    if ACCESS_TOKEN_EXPIRE_MINUTES < 1 or ACCESS_TOKEN_EXPIRE_MINUTES > 1440:  # 1 min to 24 hours
        logger.warning(
            f"⚠️  ACCESS_TOKEN_EXPIRE_MINUTES={ACCESS_TOKEN_EXPIRE_MINUTES} is outside safe range (1-1440). "
            "Using default of 15 minutes."
        )
        ACCESS_TOKEN_EXPIRE_MINUTES = 15
except ValueError:
    logger.warning(
        f"⚠️  Invalid ACCESS_TOKEN_EXPIRE_MINUTES value in environment. Using default of 15 minutes."
    )
    ACCESS_TOKEN_EXPIRE_MINUTES = 15

try:
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    if REFRESH_TOKEN_EXPIRE_DAYS < 1 or REFRESH_TOKEN_EXPIRE_DAYS > 90:  # 1 day to 90 days
        logger.warning(
            f"⚠️  REFRESH_TOKEN_EXPIRE_DAYS={REFRESH_TOKEN_EXPIRE_DAYS} is outside safe range (1-90). "
            "Using default of 7 days."
        )
        REFRESH_TOKEN_EXPIRE_DAYS = 7
except ValueError:
    logger.warning(
        f"⚠️  Invalid REFRESH_TOKEN_EXPIRE_DAYS value in environment. Using default of 7 days."
    )
    REFRESH_TOKEN_EXPIRE_DAYS = 7

# Validate JWT algorithm
SUPPORTED_ALGORITHMS = ["HS256", "HS384", "HS512"]
if ALGORITHM not in SUPPORTED_ALGORITHMS:
    logger.warning(
        f"⚠️  Unsupported JWT_ALGORITHM={ALGORITHM}. Using HS256. "
        f"Supported: {', '.join(SUPPORTED_ALGORITHMS)}"
    )
    ALGORITHM = "HS256"

# Cookie security settings based on environment
# In production: secure=True (HTTPS only), samesite=strict (no cross-site requests)
# In development: secure=False (allow HTTP), samesite=lax (allow reasonable cross-site navigation)
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
COOKIE_SECURE = is_production_like()
COOKIE_SAMESITE = "strict" if is_production_like() else "lax"
COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", None)  # e.g., ".example.com" for subdomain support

# Warn if production mode without proper HTTPS configuration
if is_production_like() and not COOKIE_SECURE:
    logger.warning(
        "⚠️  SECURITY WARNING: Running in production mode but COOKIE_SECURE is False. "
        "Refresh tokens will be sent over HTTP, which is vulnerable to MITM attacks. "
        "Ensure your application is served over HTTPS."
    )


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string

    Example:
        >>> hashed = hash_password("my_secure_password")
        >>> verify_password("my_secure_password", hashed)
        True
    """
    logger.debug("Hashing password")
    hashed = pwd_context.hash(password)
    logger.debug("Password hashed successfully")
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    logger.debug("Verifying password")
    is_valid = pwd_context.verify(plain_password, hashed_password)
    logger.debug(f"Password verification result: {is_valid}")
    return is_valid


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: Payload data to encode in the token (typically includes user_id, role)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_access_token({"sub": "1", "role": "admin"})
    """
    logger.debug(f"Creating access token for data: {data}")
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"Access token created, expires at: {expire}")
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT refresh token with a unique JTI (JWT ID) for revocation tracking.

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string

    Example:
        >>> token = create_refresh_token({"sub": "1"})
    """
    logger.debug(f"Creating refresh token for data: {data}")
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # Generate unique JTI for token revocation tracking
    jti = secrets.token_urlsafe(32)
    to_encode.update({"exp": expire, "type": "refresh", "jti": jti})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"Refresh token created with JTI: {jti}, expires at: {expire}")
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Decoded token payload if valid, None otherwise

    Example:
        >>> payload = verify_token(token)
        >>> if payload:
        ...     user_id = payload.get("sub")
    """
    logger.debug("Verifying JWT token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug(f"Token verified successfully for user: {payload.get('sub')}")
        return payload
    except JWTError as e:
        logger.info(f"JWT verification failed: {str(e)}")
        return None


def generate_api_key() -> str:
    """
    Generate a secure random API key with the format: ttk_live_<32_random_chars>

    Returns:
        API key string in format ttk_live_xxxxx

    Note:
        Only the hash of this key should be stored in the database.
        The raw key should be shown to the user only once during creation.

    Example:
        >>> api_key = generate_api_key()
        >>> api_key.startswith("ttk_live_")
        True
    """
    logger.debug("Generating new API key")
    random_part = secrets.token_urlsafe(32)
    api_key = f"ttk_live_{random_part}"
    logger.info("API key generated successfully")
    return api_key


def hash_api_key(api_key: str) -> str:
    """
    Hash an API key for secure storage.

    Args:
        api_key: Raw API key to hash

    Returns:
        Hashed API key string

    Note:
        We use the same Argon2id hashing as passwords for consistency.
    """
    logger.debug("Hashing API key")
    hashed = pwd_context.hash(api_key)
    logger.debug("API key hashed successfully")
    return hashed


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """
    Verify an API key against its hash.

    Args:
        plain_key: Plain text API key to verify
        hashed_key: Hashed API key to compare against

    Returns:
        True if key matches, False otherwise
    """
    logger.debug("Verifying API key")
    is_valid = pwd_context.verify(plain_key, hashed_key)
    logger.debug(f"API key verification result: {is_valid}")
    return is_valid
