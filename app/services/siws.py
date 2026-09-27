from __future__ import annotations

import os
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
NONCE_TTL_SECONDS = 300
NONCE_RETENTION_SECONDS = 3600
SESSION_TTL_SECONDS = 900
JWT_ALGORITHM = "HS256"
SIWS_STATEMENT = "Sign in to Sentinela Digital."


class SiwsError(ValueError):
    """Base error for SIWS challenge validation."""


class SiwsNonceUnavailable(SiwsError):
    """Nonce is unknown, already consumed, or no longer available."""


class SiwsNonceExpired(SiwsError):
    """Nonce exceeded its expiration time."""


class SiwsMessageMismatch(SiwsError):
    """Submitted SIWS message does not exactly match the server challenge."""


class SiwsInvalidSignature(SiwsError):
    """Wallet signature is invalid for the supplied public key and message."""


class SiwsConfigurationError(RuntimeError):
    """Required authentication configuration is missing or invalid."""


@dataclass(frozen=True)
class SiwsChallenge:
    nonce: str
    public_key: str
    domain: str
    uri: str
    message: str
    issued_at: datetime
    expires_at: datetime


_nonce_store: dict[str, SiwsChallenge] = {}
_nonce_lock = threading.Lock()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _base58_decode(value: str) -> bytes:
    if not value:
        raise ValueError("Base58 vazio")
    number = 0
    for character in value:
        index = BASE58_ALPHABET.find(character)
        if index < 0:
            raise ValueError("Caractere Base58 inválido")
        number = number * 58 + index
    body = number.to_bytes((number.bit_length() + 7) // 8, "big") if number else b""
    zeroes = len(value) - len(value.lstrip("1"))
    return b"\0" * zeroes + body


def _base58_encode(value: bytes) -> str:
    zeroes = len(value) - len(value.lstrip(b"\0"))
    number = int.from_bytes(value, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = BASE58_ALPHABET[remainder] + encoded
    return "1" * zeroes + (encoded or ("" if zeroes else "1"))


def _public_key_bytes(public_key: str) -> bytes:
    try:
        decoded = _base58_decode(public_key)
    except ValueError as exc:
        raise SiwsInvalidSignature("public_key precisa ser uma chave Solana Base58 válida.") from exc
    if len(decoded) != 32:
        raise SiwsInvalidSignature("public_key precisa representar exatamente 32 bytes.")
    return decoded


def _signature_bytes(signature: str) -> bytes:
    candidate = (signature or "").strip()
    hex_candidate = candidate[2:] if candidate.lower().startswith("0x") else candidate
    if len(hex_candidate) == 128:
        try:
            raw = bytes.fromhex(hex_candidate)
            if len(raw) == 64:
                return raw
        except ValueError:
            pass
    try:
        raw = _base58_decode(candidate)
    except ValueError as exc:
        raise SiwsInvalidSignature("signature deve estar em Base58 ou hexadecimal.") from exc
    if len(raw) != 64:
        raise SiwsInvalidSignature("signature deve conter 64 bytes.")
    return raw


def _message(domain: str, public_key: str, uri: str, nonce: str, issued_at: datetime, expires_at: datetime) -> str:
    return (
        f"{domain} wants you to sign in with your Solana account:\n"
        f"{public_key}\n\n"
        f"{SIWS_STATEMENT}\n\n"
        f"URI: {uri}\n"
        "Version: 1\n"
        "Chain ID: mainnet-beta\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {_format_time(issued_at)}\n"
        f"Expiration Time: {_format_time(expires_at)}"
    )


def issue_siws_challenge(
    public_key: str,
    domain: str,
    uri: str,
    *,
    now: datetime | None = None,
) -> SiwsChallenge:
    """Create and store a one-time SIWS challenge bound to a public key."""
    key_bytes = _public_key_bytes((public_key or "").strip())
    if len(key_bytes) != 32:
        raise ValueError("Chave pública Solana inválida.")
    safe_domain = (domain or "").strip()
    safe_uri = (uri or "").strip()
    if not safe_domain or any(char in safe_domain for char in "\r\n"):
        raise ValueError("Domínio SIWS inválido.")
    if not safe_uri.startswith(("https://", "http://")) or any(char in safe_uri for char in "\r\n"):
        raise ValueError("URI SIWS inválida.")

    issued_at = (now or _utc_now()).astimezone(timezone.utc).replace(microsecond=0)
    expires_at = issued_at + timedelta(seconds=NONCE_TTL_SECONDS)
    nonce = secrets.token_hex(16)
    challenge = SiwsChallenge(
        nonce=nonce,
        public_key=public_key.strip(),
        domain=safe_domain,
        uri=safe_uri,
        message=_message(safe_domain, public_key.strip(), safe_uri, nonce, issued_at, expires_at),
        issued_at=issued_at,
        expires_at=expires_at,
    )
    with _nonce_lock:
        retention_limit = issued_at - timedelta(seconds=NONCE_RETENTION_SECONDS)
        expired = [key for key, item in _nonce_store.items() if item.expires_at <= retention_limit]
        for key in expired:
            _nonce_store.pop(key, None)
        _nonce_store[nonce] = challenge
    return challenge


def verify_siws_signature(
    public_key: str,
    signature: str,
    message: str,
    nonce: str,
    *,
    now: datetime | None = None,
) -> SiwsChallenge:
    """Consume a challenge once, validate its exact message and Ed25519 signature."""
    with _nonce_lock:
        challenge = _nonce_store.pop(nonce, None)

    if challenge is None:
        raise SiwsNonceUnavailable("Nonce inexistente, já consumido ou inválido.")
    current_time = (now or _utc_now()).astimezone(timezone.utc)
    if current_time >= challenge.expires_at:
        raise SiwsNonceExpired("Nonce expirado; solicite um novo desafio.")
    if public_key.strip() != challenge.public_key:
        raise SiwsInvalidSignature("A chave pública não corresponde ao nonce.")
    if message != challenge.message:
        raise SiwsMessageMismatch("A mensagem SIWS foi alterada; solicite um novo desafio.")

    try:
        key = VerifyKey(_public_key_bytes(public_key.strip()))
        key.verify(message.encode("utf-8"), _signature_bytes(signature))
    except (BadSignatureError, ValueError) as exc:
        raise SiwsInvalidSignature("Assinatura Ed25519 inválida.") from exc
    return challenge


def get_jwt_secret() -> str:
    secret = (os.getenv("JWT_SECRET_KEY") or os.getenv("SIWS_JWT_SECRET") or "").strip()
    if len(secret) < 32:
        raise SiwsConfigurationError("Configure JWT_SECRET_KEY com pelo menos 32 caracteres aleatórios.")
    return secret


def create_session_jwt(public_key: str, domain: str, *, now: datetime | None = None) -> tuple[str, int]:
    """Issue a short-lived HS256 bearer JWT for a successfully verified wallet."""
    current_time = (now or _utc_now()).astimezone(timezone.utc)
    expires_at = current_time + timedelta(seconds=SESSION_TTL_SECONDS)
    claims: dict[str, Any] = {
        "sub": public_key,
        "wallet_address": public_key,
        "iss": domain,
        "iat": int(current_time.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    token = jwt.encode(claims, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return token, SESSION_TTL_SECONDS


def _clear_nonce_store() -> None:
    """Clear the in-memory challenge cache; intended for test isolation."""
    with _nonce_lock:
        _nonce_store.clear()
