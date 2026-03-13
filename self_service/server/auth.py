"""RS256 JWT helpers for node-to-cloud authentication."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

DEFAULT_ISSUER = "coda"
DEFAULT_TTL = timedelta(hours=1)
KEY_SIZE = 2048


@dataclass(frozen=True, slots=True)
class KeyPair:
    """RSA keypair for JWT authentication."""

    private_key_pem: str
    public_key_pem: str
    key_id: str


def generate_keypair(key_id: str) -> KeyPair:
    """Generate a PEM-encoded RSA keypair."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=KEY_SIZE)

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )

    return KeyPair(
        private_key_pem=private_pem,
        public_key_pem=public_pem,
        key_id=key_id,
    )


def sign_token(
    subject: str,
    private_key_pem: str,
    *,
    issuer: str = DEFAULT_ISSUER,
    ttl: timedelta = DEFAULT_TTL,
    key_id: str | None = None,
) -> str:
    """Create a signed JWT."""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "iss": issuer,
        "iat": now,
        "exp": now + ttl,
    }
    headers = {"kid": key_id or subject}
    return jwt.encode(payload, private_key_pem, algorithm="RS256", headers=headers)


def verify_token(
    token: str,
    get_public_key: Callable[[str], str | None],
    *,
    issuer: str = DEFAULT_ISSUER,
) -> dict[str, object]:
    """Verify a JWT using public key lookup via its ``kid`` header."""
    try:
        header = jwt.get_unverified_header(token)
    except jwt.DecodeError as exc:
        raise jwt.InvalidTokenError(f"Malformed token header: {exc}") from exc

    kid = header.get("kid")
    if not kid:
        raise jwt.InvalidTokenError("Token missing 'kid' header")

    public_key_pem = get_public_key(kid)
    if not public_key_pem:
        raise jwt.InvalidTokenError(f"Unknown key_id: {kid}")

    result: dict[str, object] = jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        issuer=issuer,
        options={"require": ["sub", "iss", "exp", "iat"]},
    )
    return result


def verify_token_with_key(
    token: str,
    public_key_pem: str,
    *,
    issuer: str = DEFAULT_ISSUER,
) -> dict[str, object]:
    """Verify a JWT with a known public key."""
    result: dict[str, object] = jwt.decode(
        token,
        public_key_pem,
        algorithms=["RS256"],
        issuer=issuer,
        options={"require": ["sub", "iss", "exp", "iat"]},
    )
    return result
