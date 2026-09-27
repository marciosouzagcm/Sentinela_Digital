from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("sentinela")

SOLANA_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")
SOLANA_DOMAIN_RE = re.compile(r"(?i)^[a-z0-9-]+(?:\.[a-z0-9-]+)*\.sol\.?$")
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"
DEFAULT_SNS_RESOLVER_URL = "https://sns-api.bonfida.com/resolve"
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
KNOWN_TOKEN_SYMBOLS = {
    # Common mainnet mints; unknown mints are deliberately identified by prefix only.
    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
    "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
    "So11111111111111111111111111111111111111112": "wSOL",
}

try:  # pragma: no cover - import compatibility depends on installed solana stack
    from solders.pubkey import Pubkey  # type: ignore
except Exception:  # pragma: no cover
    try:
        from solana.publickey import PublicKey as Pubkey  # type: ignore
    except Exception:  # pragma: no cover
        Pubkey = None  # type: ignore


def _rpc_urls() -> list[str]:
    cluster = os.getenv("SOLANA_ENV", "mainnet-beta").strip().lower()
    cluster = {"mainnet": "mainnet-beta", "mainnet-beta": "mainnet-beta", "devnet": "devnet"}.get(cluster)
    if cluster is None:
        raise ValueError("SOLANA_ENV deve ser 'mainnet-beta' ou 'devnet'.")
    public_endpoint = f"https://api.{cluster}.solana.com"
    raw = os.getenv("SOLANA_RPC_URLS") or os.getenv("SOLANA_RPC_URL") or ""
    configured = [url.strip() for url in raw.split(",") if url.strip()]
    return list(dict.fromkeys([*configured, public_endpoint]))


def _parse_json_env(name: str) -> dict[str, Any]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Environment variable %s does not contain valid JSON.", name)
        return {}
    if isinstance(value, dict):
        return {str(key).lower(): val for key, val in value.items()}
    if isinstance(value, list):
        return {str(item).lower(): {"label": "flagged", "source": name} for item in value if item}
    return {}


def _is_solana_address(value: str) -> bool:
    candidate = (value or "").strip()
    if not SOLANA_ADDRESS_RE.fullmatch(candidate):
        return False
    if Pubkey is None:
        leading_zeroes = len(candidate) - len(candidate.lstrip("1"))
        numeric_value = 0
        for character in candidate:
            numeric_value = numeric_value * 58 + BASE58_ALPHABET.index(character)
        decoded_bytes = (numeric_value.bit_length() + 7) // 8
        return leading_zeroes + decoded_bytes == 32
    try:
        if hasattr(Pubkey, "from_string"):
            Pubkey.from_string(candidate)
        else:
            Pubkey(candidate)
        return True
    except Exception:
        return False


def is_solana_address(value: str) -> bool:
    """Public validator for a 32-byte Solana address encoded as Base58."""
    return _is_solana_address(value)


def _pubkey(value: str) -> Any:
    if Pubkey is None:
        return value.strip()
    candidate = value.strip()
    if hasattr(Pubkey, "from_string"):
        return Pubkey.from_string(candidate)
    return Pubkey(candidate)


async def _rpc_request(method: str, params: list[Any]) -> tuple[str, dict[str, Any]]:
    errors: list[Exception] = []
    endpoints = _rpc_urls()
    for endpoint in endpoints:
        try:
            async with httpx.AsyncClient(timeout=float(os.getenv("SOLANA_RPC_TIMEOUT_SECONDS", "12"))) as client:
                response = await client.post(
                    endpoint,
                    json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                payload = response.json()
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(str(payload["error"]))
            return endpoint, payload
        except Exception as exc:
            errors.append(exc)
    reason = type(errors[-1]).__name__ if errors else "no RPC endpoints configured"
    raise RuntimeError(f"RPC {method} failed for {len(endpoints)} configured endpoint(s) ({reason}).")


def _extract_value(payload: dict[str, Any]) -> Any:
    result = payload.get("result") if isinstance(payload, dict) else None
    return result.get("value") if isinstance(result, dict) else None


def _format_token_entry(item: dict[str, Any]) -> dict[str, Any]:
    parsed = (((item.get("account") or {}).get("data") or {}).get("parsed") or {})
    info = parsed.get("info") or {}
    token_amount = info.get("tokenAmount") or {}
    amount = token_amount.get("uiAmount")
    if amount is None:
        raw_amount = token_amount.get("amount")
        decimals = int(token_amount.get("decimals") or 0)
        try:
            amount = (int(raw_amount) / (10 ** decimals)) if raw_amount is not None else None
        except Exception:
            amount = None
    mint = info.get("mint")
    metadata = _parse_json_env("SOLANA_TOKEN_METADATA_JSON").get(str(mint).lower(), {})
    if isinstance(metadata, str):
        metadata = {"symbol": metadata}
    symbol = metadata.get("symbol") if isinstance(metadata, dict) else None
    return {
        "mint": mint,
        "token_account": item.get("pubkey"),
        "amount": amount,
        "decimals": token_amount.get("decimals"),
        "symbol": symbol or KNOWN_TOKEN_SYMBOLS.get(str(mint), str(mint or "unknown")[:8]),
    }


def _load_flagged_addresses() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for env_name, sanctioned in (
        ("SOLANA_FLAGGED_ADDRESSES_JSON", False),
        ("SOLANA_SANCTIONED_ADDRESSES_JSON", True),
    ):
        for address, value in _parse_json_env(env_name).items():
            details = value if isinstance(value, dict) else {"label": str(value)}
            merged.setdefault(address, {"flags": []})["flags"].append(
                {**details, "source": details.get("source", env_name), "sanctioned": sanctioned}
            )
    return merged


def _load_sns_map() -> dict[str, Any]:
    return _parse_json_env("SOLANA_SNS_STATIC_MAP_JSON")


async def _get_wallet_balance_result(pubkey: str) -> tuple[float | None, str | None]:
    try:
        candidate = (pubkey or "").strip()
        if not _is_solana_address(candidate):
            raise ValueError("Endereço Solana inválido.")
        _, payload = await _rpc_request("getBalance", [candidate, {"commitment": "confirmed"}])
        value = _extract_value(payload)
        if not isinstance(value, (int, float)):
            raise RuntimeError("O RPC não retornou um saldo válido.")
        return float(value) / 1_000_000_000, None
    except Exception as exc:
        return None, f"balance: {type(exc).__name__}"


async def get_wallet_balance(pubkey: str) -> float:
    """Return confirmed SOL balance; gracefully fall back to 0.0 on errors."""
    balance, error = await _get_wallet_balance_result(pubkey)
    if error:
        logger.warning("Consulta de saldo Solana indisponível (%s). Retornando 0 SOL.", error)
        return 0.0
    return balance or 0.0


async def _get_spl_tokens_result(pubkey: str) -> tuple[list[dict[str, Any]], list[str]]:
    try:
        candidate = (pubkey or "").strip()
        if not _is_solana_address(candidate):
            raise ValueError("Endereço Solana inválido.")

        entries: list[dict[str, Any]] = []
        errors: list[str] = []
        for program_id in (TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID):
            try:
                _, payload = await _rpc_request(
                    "getTokenAccountsByOwner",
                    [candidate, {"programId": program_id, "encoding": "jsonParsed", "commitment": "confirmed"}],
                )
                value = _extract_value(payload) or []
                entries.extend(_format_token_entry(item) for item in value if isinstance(item, dict))
            except Exception as exc:
                errors.append(type(exc).__name__)
                logger.warning("Falha na consulta SPL/Token-2022 (%s).", type(exc).__name__)
        if len(errors) == 2:
            return [], ["tokens: falha nos programas SPL e Token-2022"]
        tokens = [entry for entry in entries if entry.get("amount") not in (None, 0, 0.0)]
        partial_errors = ["tokens: consulta parcial de SPL/Token-2022"] if errors else []
        return tokens, partial_errors
    except Exception as exc:
        logger.warning("Consulta de tokens SPL indisponível (%s). Retornando lista vazia.", type(exc).__name__)
        return [], [f"tokens: {type(exc).__name__}"]


async def get_spl_tokens(pubkey: str) -> list[dict[str, Any]]:
    """Return non-zero SPL and Token-2022 holdings; fall back to [] on errors."""
    tokens, _ = await _get_spl_tokens_result(pubkey)
    return tokens


async def resolve_sns_domain(domain_or_pubkey: str) -> str:
    """Resolve a .sol name to a validated public key, or pass through a valid key."""
    candidate = (domain_or_pubkey or "").strip()
    if _is_solana_address(candidate):
        return candidate
    if not SOLANA_DOMAIN_RE.fullmatch(candidate):
        raise ValueError("Informe uma PubKey Solana válida ou um domínio .sol.")

    domain = candidate.lower().rstrip(".")
    mapped = _load_sns_map().get(domain)
    if isinstance(mapped, str) and _is_solana_address(mapped):
        return mapped
    if isinstance(mapped, dict):
        address = mapped.get("address") or mapped.get("wallet")
        if isinstance(address, str) and _is_solana_address(address):
            return address

    resolver_url = os.getenv("SOLANA_SNS_RESOLVER_URL", DEFAULT_SNS_RESOLVER_URL).strip()
    try:
        async with httpx.AsyncClient(timeout=float(os.getenv("SOLANA_SNS_TIMEOUT_SECONDS", "10"))) as client:
            response = await client.get(
                f"{resolver_url.rstrip('/')}/{domain}",
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        address = body.get("address") or body.get("wallet") or body.get("result") if isinstance(body, dict) else None
        if isinstance(address, str) and _is_solana_address(address):
            return address
    except Exception as exc:
        raise RuntimeError(f"Falha ao consultar o resolvedor SNS ({type(exc).__name__}).") from exc
    raise RuntimeError(f"O domínio SNS {domain} não foi resolvido para uma PubKey válida.")


async def check_sanctions_and_flags(pubkey: str) -> dict[str, Any]:
    """Check the configured local address list and return a risk level and score."""
    candidate = (pubkey or "").strip()
    try:
        if not _is_solana_address(candidate):
            raise ValueError("Endereço Solana inválido.")
        entry = _load_flagged_addresses().get(candidate.lower(), {"flags": []})
        flags = entry.get("flags", [])
        sanctioned = any(flag.get("sanctioned", False) for flag in flags)
        configured_risks = [str(flag.get("risk_level", "")).lower() for flag in flags]
        if sanctioned or "critical" in configured_risks or "critica" in configured_risks:
            risk_level, risk_score = "critical", 100
        elif flags:
            risk_priority = {"high": 3, "alta": 3, "medium": 2, "media": 2, "low": 1, "baixa": 1}
            selected_risk = max(configured_risks, key=lambda value: risk_priority.get(value, 0), default="high")
            risk_level, risk_score = {
                3: ("high", 75),
                2: ("medium", 50),
                1: ("low", 25),
                0: ("high", 75),
            }[risk_priority.get(selected_risk, 0)]
        else:
            risk_level, risk_score = "none", 0
        return {
            "address": candidate,
            "flagged": bool(flags),
            "sanctioned": sanctioned,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "flags": flags,
            "source": "local_config",
            "disclaimer": "Checagem baseada somente em listas locais configuradas; não constitui determinação legal.",
        }
    except Exception as exc:
        logger.warning("Verificação local de sanções indisponível (%s).", type(exc).__name__)
        return {
            "address": candidate,
            "flagged": False,
            "sanctioned": False,
            "risk_level": "unknown",
            "risk_score": 0,
            "flags": [],
            "source": "local_config_unavailable",
            "error": type(exc).__name__,
            "disclaimer": "A validação falhou; ausência de sinalização não deve ser interpretada como aprovação.",
        }


async def scan_solana_target(target: str, output_dir: str | Path | None = None) -> dict[str, Any]:
    """Scan a wallet or SNS name and return partial data if an upstream fails."""

    target_value = (target or "").strip()
    output_file = Path(output_dir) / "solana.json" if output_dir else None
    result: dict[str, Any] = {
        "target": target_value,
        "target_type": "unknown",
        "wallet_address": None,
        "sol_balance": None,
        "token_accounts": [],
        "sns": {"requested": None, "resolved_address": None, "status": "not_checked"},
        "flags": [],
        "recent_signatures": [],
        "errors": [],
    }

    if not target_value:
        result["errors"].append("Target Solana ausente.")
        return {"status": "warning", "output_file": str(output_file) if output_file else None, "data": {"result": result}}

    if SOLANA_DOMAIN_RE.fullmatch(target_value):
        domain = target_value.lower().rstrip(".")
        result["target_type"] = "domain"
        result["sns"]["requested"] = domain
        try:
            resolved = await resolve_sns_domain(domain)
            static_entry = _load_sns_map().get(domain)
            result["sns"] = {
                "requested": domain,
                "resolved_address": resolved,
                "status": "resolved_static" if static_entry else "resolved_remote",
            }
            if isinstance(static_entry, dict) and static_entry.get("label"):
                result["sns"]["label"] = static_entry["label"]
            target_address = resolved
        except Exception as exc:
            result["sns"].update({"status": "unavailable", "reason": str(exc)})
            result["errors"].append(f"sns: {exc}")
            target_address = None
    elif _is_solana_address(target_value):
        target_address = target_value
        result["target_type"] = "wallet"
    else:
        result["errors"].append("Target não é um endereço Solana nem um domínio .sol válido.")
        return {"status": "unavailable", "output_file": str(output_file) if output_file else None, "data": {"result": result}}

    if target_address:
        result["wallet_address"] = target_address
        try:
            risk = await check_sanctions_and_flags(target_address)
            result["flags"] = risk["flags"]
            result["risk"] = risk
            result["flagged"] = risk["flagged"]
        except Exception as exc:
            result["errors"].append(f"flags: {exc}")

        result["sol_balance"], balance_error = await _get_wallet_balance_result(target_address)
        if balance_error:
            logger.warning("Não foi possível consultar saldo SOL para %s (%s).", target_address, balance_error)
            result["errors"].append(balance_error)

        result["token_accounts"], token_errors = await _get_spl_tokens_result(target_address)
        result["errors"].extend(token_errors)

        try:
            _, signatures_payload = await _rpc_request(
                "getSignaturesForAddress",
                [target_address, {"limit": 10, "commitment": "confirmed"}],
            )
            result["recent_signatures"] = [
                {
                    "signature": item.get("signature"),
                    "slot": item.get("slot"),
                    "err": item.get("err"),
                    "status": item.get("confirmationStatus") or item.get("confirmation_status"),
                }
                for item in (_extract_value(signatures_payload) or [])
                if isinstance(item, dict)
            ]
        except Exception as exc:
            logger.warning("Não foi possível consultar assinaturas recentes para %s: %s", target_address, exc)
            result["errors"].append(f"signatures: {exc}")

    if target_address and result["errors"]:
        status = "partial"
    elif target_address and result.get("flagged"):
        status = "warning"
    elif target_address:
        status = "success"
    else:
        status = "warning"

    payload = {"result": result}
    if output_file:
        try:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError as exc:
            logger.warning("Não foi possível persistir o resultado Solana: %s", exc)
    return {"status": status, "output_file": str(output_file) if output_file else None, "data": payload}


def run_solana_scan(target: str, output_dir: str | Path | None = None) -> dict[str, Any]:
    """Synchronous wrapper for the async Solana scan pipeline."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(scan_solana_target(target, output_dir))
    raise RuntimeError("run_solana_scan cannot be called from an active event loop; await scan_solana_target instead.")
