"""HTTP Basic and Digest Authentication implementation.

Provides password protection for the web interface and API using either:
- HTTP Basic Auth (RFC 7617) - simple, widely supported, base64-encoded credentials
- HTTP Digest Auth (RFC 7616) - challenge-response, prevents cleartext transmission

The authentication is enabled only if both AUTH_USERNAME and AUTH_PASSWORD are set
in the configuration (.env file). Use AUTH_SCHEME to choose between "basic" or "digest".
"""

import hashlib
import secrets
import time
import base64
from typing import Optional, Dict
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from src.bcd_api.core.config import settings


# Realm for HTTP Digest Auth
REALM = "BCD Library System"

# Store active nonces with their creation timestamp
# Format: {nonce: timestamp}
_nonces: Dict[str, float] = {}

# Nonce validity duration in seconds (5 minutes)
NONCE_LIFETIME = 300


def is_auth_enabled() -> bool:
    """Check if authentication is enabled.

    Returns:
        True if both username and password are configured, False otherwise.
    """
    return bool(settings.auth_username and settings.auth_password)


def generate_nonce() -> str:
    """Generate a cryptographically secure nonce.

    Returns:
        Hex-encoded random nonce.
    """
    return secrets.token_hex(16)


def cleanup_old_nonces() -> None:
    """Remove expired nonces from the store."""
    now = time.time()
    expired = [nonce for nonce, timestamp in _nonces.items()
               if now - timestamp > NONCE_LIFETIME]
    for nonce in expired:
        del _nonces[nonce]


def validate_nonce(nonce: str) -> bool:
    """Check if a nonce is valid (exists and not expired).

    Args:
        nonce: The nonce to validate.

    Returns:
        True if the nonce is valid, False otherwise.
    """
    cleanup_old_nonces()
    if nonce not in _nonces:
        return False

    timestamp = _nonces[nonce]
    return (time.time() - timestamp) <= NONCE_LIFETIME


def create_nonce() -> str:
    """Create a new nonce and store it.

    Returns:
        The newly created nonce.
    """
    cleanup_old_nonces()
    nonce = generate_nonce()
    _nonces[nonce] = time.time()
    return nonce


def compute_ha1(username: str, password: str, realm: str = REALM) -> str:
    """Compute HA1 hash for Digest Auth.

    HA1 = MD5(username:realm:password)

    Args:
        username: Username.
        password: Password.
        realm: Authentication realm.

    Returns:
        Hex-encoded MD5 hash.
    """
    ha1_str = f"{username}:{realm}:{password}"
    return hashlib.md5(ha1_str.encode()).hexdigest()


def compute_ha2(method: str, uri: str) -> str:
    """Compute HA2 hash for Digest Auth.

    HA2 = MD5(method:uri)

    Args:
        method: HTTP method (GET, POST, etc.).
        uri: Request URI.

    Returns:
        Hex-encoded MD5 hash.
    """
    ha2_str = f"{method}:{uri}"
    return hashlib.md5(ha2_str.encode()).hexdigest()


def compute_response(ha1: str, nonce: str, ha2: str, qop: Optional[str] = None,
                    nc: Optional[str] = None, cnonce: Optional[str] = None) -> str:
    """Compute the response hash for Digest Auth.

    Without qop: response = MD5(HA1:nonce:HA2)
    With qop:    response = MD5(HA1:nonce:nc:cnonce:qop:HA2)

    Args:
        ha1: HA1 hash.
        nonce: Server nonce.
        ha2: HA2 hash.
        qop: Quality of protection (auth, auth-int, or None).
        nc: Nonce count (hex).
        cnonce: Client nonce.

    Returns:
        Hex-encoded MD5 hash.
    """
    if qop:
        response_str = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"
    else:
        response_str = f"{ha1}:{nonce}:{ha2}"
    return hashlib.md5(response_str.encode()).hexdigest()


def parse_digest_header(auth_header: str) -> Dict[str, str]:
    """Parse HTTP Digest Authorization header.

    Args:
        auth_header: The Authorization header value (without "Digest " prefix).

    Returns:
        Dictionary of parsed parameters.
    """
    params = {}
    for item in auth_header.split(","):
        item = item.strip()
        if "=" in item:
            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"')
            params[key] = value
    return params


def validate_digest_auth(request: Request, auth_header: str) -> bool:
    """Validate HTTP Digest Authentication header.

    Args:
        request: The FastAPI request object.
        auth_header: The Authorization header value.

    Returns:
        True if authentication is valid, False otherwise.
    """
    if not auth_header.startswith("Digest "):
        return False

    try:
        params = parse_digest_header(auth_header[7:])  # Remove "Digest " prefix

        # Extract required parameters
        username = params.get("username")
        realm = params.get("realm")
        nonce = params.get("nonce")
        uri = params.get("uri")
        response = params.get("response")
        qop = params.get("qop")
        nc = params.get("nc")
        cnonce = params.get("cnonce")

        # Validate required fields
        if not all([username, realm, nonce, uri, response]):
            return False

        # Check username matches configuration
        if username != settings.auth_username:
            return False

        # Check realm matches
        if realm != REALM:
            return False

        # Validate nonce
        if not validate_nonce(nonce):
            return False

        # Compute expected response
        ha1 = compute_ha1(settings.auth_username, settings.auth_password, REALM)
        ha2 = compute_ha2(request.method, uri)
        expected_response = compute_response(ha1, nonce, ha2, qop, nc, cnonce)

        # Compare responses
        return response == expected_response

    except Exception:
        return False


def validate_basic_auth(auth_header: str) -> bool:
    """Validate HTTP Basic Authentication header.

    Args:
        auth_header: The Authorization header value.

    Returns:
        True if authentication is valid, False otherwise.
    """
    if not auth_header.startswith("Basic "):
        return False

    try:
        # Decode base64 credentials
        encoded_credentials = auth_header[6:]  # Remove "Basic " prefix
        decoded_bytes = base64.b64decode(encoded_credentials)
        decoded_credentials = decoded_bytes.decode('utf-8')

        # Split username:password
        if ':' not in decoded_credentials:
            return False

        username, password = decoded_credentials.split(':', 1)

        # Validate credentials
        return (username == settings.auth_username and
                password == settings.auth_password)

    except Exception:
        return False


def create_auth_challenge(stale: bool = False) -> str:
    """Create a WWW-Authenticate header value for Basic or Digest Auth.

    Args:
        stale: If True (Digest only), indicates the nonce has expired.

    Returns:
        WWW-Authenticate header value.
    """
    scheme = settings.auth_scheme.lower()

    if scheme == "basic":
        return f'Basic realm="{REALM}"'
    else:  # digest
        nonce = create_nonce()
        challenge = f'Digest realm="{REALM}", qop="auth", nonce="{nonce}", algorithm=MD5'
        if stale:
            challenge += ', stale=true'
        return challenge


class HTTPAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce HTTP Basic or Digest Authentication on all routes."""

    async def dispatch(self, request: Request, call_next):
        """Process the request and enforce authentication if enabled.

        Args:
            request: The incoming request.
            call_next: The next middleware/endpoint in the chain.

        Returns:
            Response from the endpoint or 401 Unauthorized.
        """
        # Skip authentication if not enabled
        if not is_auth_enabled():
            return await call_next(request)

        # Public routes that don't require authentication
        public_paths = [
            "/health",  # Health check endpoint
            "/api/v1/collections/peers",  # mDNS peer discovery — public by design
        ]

        # Check if this is a public path
        if request.url.path in public_paths:
            return await call_next(request)

        # Check for Authorization header
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            # No credentials provided, send challenge
            return Response(
                content="Unauthorized",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": create_auth_challenge()},
            )

        # Validate credentials based on configured scheme
        scheme = settings.auth_scheme.lower()
        is_valid = False

        if scheme == "basic":
            is_valid = validate_basic_auth(auth_header)
        else:  # digest
            is_valid = validate_digest_auth(request, auth_header)

        if not is_valid:
            # Invalid credentials, send challenge
            stale = False

            # For Digest auth, check if nonce expired
            if scheme == "digest" and auth_header.startswith("Digest "):
                params = parse_digest_header(auth_header[7:])
                nonce = params.get("nonce")
                if nonce and not validate_nonce(nonce):
                    stale = True

            return Response(
                content="Unauthorized",
                status_code=status.HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": create_auth_challenge(stale=stale)},
            )

        # Authentication successful, proceed with request
        return await call_next(request)


# Legacy alias for backward compatibility
DigestAuthMiddleware = HTTPAuthMiddleware
