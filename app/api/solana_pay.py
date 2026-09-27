from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import AliasChoices, BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import PaymentTransaction, ScanCreditLedger, User
from app.services.mod_solana import is_solana_address
from app.services.solana_reporting import generate_solana_report

try:  # pragma: no cover - import compatibility depends on installed solana stack
    from solders.pubkey import Pubkey  # type: ignore
except Exception:  # pragma: no cover
    try:
        from solana.publickey import PublicKey as Pubkey  # type: ignore
    except Exception:  # pragma: no cover
        Pubkey = None  # type: ignore

router = APIRouter(prefix="/api/v1")

DEFAULT_AMOUNT_SOL = float(os.getenv("SOLANA_PAY_DEFAULT_AMOUNT_SOL", "0.05"))
NONCE_TTL_SECONDS = 300


class CreateOrderRequest(BaseModel):
    wallet_address: str = Field(..., min_length=32, max_length=88)
    amount_sol: float = Field(default=DEFAULT_AMOUNT_SOL, gt=0)
    scans_to_credit: int = Field(default=1, ge=1)
    target: str | None = Field(default=None, max_length=255)
    note: str | None = None


class CreateOrderResponse(BaseModel):
    ok: bool
    order_id: str
    reference: str
    recipient: str
    amount_sol: float
    payment_url: str
    qr_payload: str
    expires_at: int


class VerifyPaymentRequest(BaseModel):
    reference: str = Field(..., min_length=32)
    tx_signature: str | None = Field(default=None, validation_alias=AliasChoices("txSignature", "tx_signature"))
    wallet_address: str | None = Field(default=None, min_length=32, max_length=88)
    scans_to_credit: int = Field(default=1, ge=1)
    expected_amount_sol: float | None = Field(default=None, gt=0)


class VerifyPaymentResponse(BaseModel):
    ok: bool
    status: str
    message: str
    reference: str
    signature: str | None = None
    credits_added: int = 0
    wallet_address: str | None = None
    payment_url: str | None = None


def _make_reference() -> str:
    if Pubkey is None:
        return os.urandom(32).hex()[:44]
    seed = os.urandom(32)
    if hasattr(Pubkey, "from_bytes"):
        return str(Pubkey.from_bytes(seed))
    if hasattr(Pubkey, "new_unique"):
        return str(Pubkey.new_unique())
    return os.urandom(32).hex()[:44]


def _is_pubkey(value: str | None) -> bool:
    return is_solana_address((value or "").strip())


def _payment_recipient() -> str:
    recipient = (
        os.getenv("SOLANA_TREASURY_WALLET")
        or os.getenv("SOLANA_PAY_RECIPIENT")
        or os.getenv("SOLANA_PAY_MERCHANT_ADDRESS")
        or ""
    ).strip()
    if not _is_pubkey(recipient):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Defina SOLANA_TREASURY_WALLET ou SOLANA_PAY_RECIPIENT com uma chave pública Solana válida.",
        )
    return recipient


def _payment_url(recipient: str, amount_sol: float, reference: str, label: str, message: str) -> str:
    params = [
        ("amount", f"{amount_sol:.9f}".rstrip("0").rstrip(".")),
        ("reference", reference),
        ("label", label),
        ("message", message),
    ]
    query = "&".join(f"{key}={requests.utils.quote(value)}" for key, value in params if value)
    return f"solana:{recipient}?{query}"


def _safe_json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _user_by_wallet(db: Session, wallet_address: str | None) -> User | None:
    if not wallet_address:
        return None
    return db.execute(select(User).where(User.wallet_address == wallet_address)).scalar_one_or_none()


def _order_by_reference(db: Session, reference: str) -> PaymentTransaction | None:
    return db.execute(
        select(PaymentTransaction).where(PaymentTransaction.signature == reference).with_for_update()
    ).scalar_one_or_none()


def _rpc_urls() -> list[str]:
    cluster = os.getenv("SOLANA_ENV", "mainnet-beta").strip().lower()
    cluster = {"mainnet": "mainnet-beta", "mainnet-beta": "mainnet-beta", "devnet": "devnet"}.get(cluster)
    if cluster is None:
        raise ValueError("SOLANA_ENV deve ser 'mainnet-beta' ou 'devnet'.")
    public_endpoint = f"https://api.{cluster}.solana.com"
    raw = os.getenv("SOLANA_RPC_URLS") or os.getenv("SOLANA_RPC_URL") or ""
    configured = [url.strip() for url in raw.split(",") if url.strip()]
    return list(dict.fromkeys([*configured, public_endpoint]))


def _rpc_request_sync(endpoint: str, method: str, params: list[Any]) -> dict[str, Any]:
    response = requests.post(
        endpoint,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=float(os.getenv("SOLANA_RPC_TIMEOUT_SECONDS", "12")),
        headers={"Content-Type": "application/json"},
    )
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(str(payload["error"]))
    return payload if isinstance(payload, dict) else {}


def _rpc_request(method: str, params: list[Any]) -> dict[str, Any]:
    errors: list[str] = []
    for endpoint in _rpc_urls():
        try:
            return _rpc_request_sync(endpoint, method, params)
        except Exception as exc:
            errors.append(type(exc).__name__)
    raise RuntimeError(f"RPC {method} falhou em {len(errors)} endpoint(s): {', '.join(errors)}")


def _extract_value(payload: dict[str, Any]) -> Any:
    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, dict):
        return result.get("value")
    return None


def _signatures_for_reference(reference: str) -> list[dict[str, Any]]:
    payload = _rpc_request("getSignaturesForAddress", [reference, {"limit": 10, "commitment": "confirmed"}])
    value = _extract_value(payload)
    return [item for item in value or [] if isinstance(item, dict)]


def _transaction_matches_order(
    signature: str,
    metadata: dict[str, Any],
    expected_lamports: int,
    expected_reference: str | None = None,
) -> bool:
    """Validate treasury, amount and expected wallet against the confirmed transaction."""
    recipient = metadata.get("recipient")
    wallet_address = metadata.get("wallet_address")
    if not isinstance(recipient, str) or not _is_pubkey(recipient) or not isinstance(wallet_address, str):
        return False

    payload = _rpc_request(
        "getTransaction",
        [signature, {"encoding": "jsonParsed", "commitment": "confirmed", "maxSupportedTransactionVersion": 0}],
    )
    transaction = (payload.get("result") or {}).get("transaction") or {}
    message = transaction.get("message") or {}
    transaction_meta = (payload.get("result") or {}).get("meta") or {}
    if transaction_meta.get("err") is not None:
        return False
    account_keys = message.get("accountKeys") or []
    key_strings = {
        str(item.get("pubkey")) if isinstance(item, dict) else str(item)
        for item in account_keys
    }
    if expected_reference and expected_reference not in key_strings:
        return False
    signers = {
        str(item.get("pubkey"))
        for item in account_keys
        if isinstance(item, dict) and item.get("signer")
    }
    if wallet_address not in signers:
        return False

    transferred_lamports = 0
    for instruction in message.get("instructions") or []:
        if not isinstance(instruction, dict):
            continue
        parsed = instruction.get("parsed") or {}
        info = parsed.get("info") or {}
        if instruction.get("program") == "system" and parsed.get("type") == "transfer" and info.get("destination") == recipient:
            try:
                transferred_lamports += int(info.get("lamports", 0))
            except (TypeError, ValueError):
                continue
    return transferred_lamports >= expected_lamports


def _signature_is_confirmed(signature: str) -> bool:
    payload = _rpc_request("getSignatureStatuses", [[signature], {"searchTransactionHistory": True}])
    values = _extract_value(payload) or []
    if not values or not isinstance(values[0], dict):
        return False
    confirmation = str(values[0].get("confirmationStatus") or "").lower()
    return values[0].get("err") is None and confirmation in {"confirmed", "finalized"}


async def _run_paid_solana_scan(target: str, reference: str, signature: str) -> None:
    try:
        await generate_solana_report(
            target,
            payment={"reference": reference, "signature": signature},
        )
    except Exception:
        import logging

        logging.getLogger("sentinela").exception("Varredura Solana pós-pagamento falhou para referência %s.", reference)


@router.post("/payments/create-order", response_model=CreateOrderResponse)
def create_order(payload: CreateOrderRequest, db: Session = Depends(get_db)) -> CreateOrderResponse:
    recipient = _payment_recipient()
    reference = _make_reference()
    label = "Sentinela Digital"
    wallet_address = payload.wallet_address.strip()
    if not _is_pubkey(wallet_address):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallet_address inválida.")
    target = payload.target.strip() if payload.target else None
    if payload.target is not None and (not target or any(ord(character) < 32 for character in target)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="target deve ser um texto válido de até 255 caracteres.")
    payment_url = _payment_url(
        recipient=recipient,
        amount_sol=payload.amount_sol,
        reference=reference,
        label=label,
        message=payload.note or "Pagamentos por varredura Solana on-chain",
    )

    order = PaymentTransaction(
        user_uuid=wallet_address or reference,
        signature=reference,
        amount_lamports=int(payload.amount_sol * 1_000_000_000),
        token_mint=None,
        currency="SOL",
        status="pending",
        user_metadata=json.dumps(
            {
                "reference": reference,
                "wallet_address": wallet_address,
                "target": target,
                "note": payload.note,
                "payment_url": payment_url,
                "scans_to_credit": payload.scans_to_credit,
                "amount_sol": payload.amount_sol,
                "recipient": recipient,
            },
            ensure_ascii=False,
        ),
    )
    db.add(order)
    db.commit()

    return CreateOrderResponse(
        ok=True,
        order_id=reference,
        reference=reference,
        recipient=recipient,
        amount_sol=payload.amount_sol,
        payment_url=payment_url,
        qr_payload=payment_url,
        expires_at=int(datetime.now(timezone.utc).timestamp()) + NONCE_TTL_SECONDS,
    )


@router.post("/payments/verify-payment", response_model=VerifyPaymentResponse)
def verify_payment(
    payload: VerifyPaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> VerifyPaymentResponse:
    reference = payload.reference.strip()
    if not _is_pubkey(reference):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="reference inválida.")

    order = _order_by_reference(db, reference)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ordem de pagamento não encontrada.")

    order_metadata = _safe_json_loads(order.user_metadata)
    if order.status == "verified":
        return VerifyPaymentResponse(
            ok=True,
            status="verified",
            message="Pagamento já confirmado; créditos não foram duplicados.",
            reference=reference,
            signature=order_metadata.get("confirmed_signature"),
            credits_added=int(order_metadata.get("credits_added") or 0),
            wallet_address=_load_wallet_from_order(order),
            payment_url=order_metadata.get("payment_url"),
        )

    wallet_address = _load_wallet_from_order(order)
    if payload.wallet_address and wallet_address and payload.wallet_address.strip() != wallet_address:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="A carteira informada não corresponde à ordem.")
    wallet_address = wallet_address or payload.wallet_address
    if wallet_address and not _is_pubkey(wallet_address):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallet_address inválida.")
    if not wallet_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="wallet_address é obrigatório para liberar créditos quando o pedido não possui metadados de carteira.",
        )

    confirmed_signature = None
    if payload.tx_signature:
        confirmed_signature = payload.tx_signature.strip()
        try:
            if not _signature_is_confirmed(confirmed_signature):
                return VerifyPaymentResponse(
                    ok=False,
                    status="pending",
                    message="A assinatura informada ainda não está confirmada na rede selecionada.",
                    reference=reference,
                    wallet_address=wallet_address,
                )
        except Exception as exc:
            return VerifyPaymentResponse(
                ok=False,
                status="error",
                message=f"Falha ao consultar status da assinatura no RPC ({type(exc).__name__}).",
                reference=reference,
                wallet_address=wallet_address,
            )
    else:
        try:
            signatures = _signatures_for_reference(reference)
        except Exception as exc:
            return VerifyPaymentResponse(
                ok=False,
                status="error",
                message=f"Falha ao consultar o RPC da Solana ({type(exc).__name__}).",
                reference=reference,
                wallet_address=wallet_address,
            )
        for item in signatures:
            status_name = str(item.get("confirmationStatus") or item.get("confirmation_status") or "").lower()
            err = item.get("err")
            if err is None and status_name in {"confirmed", "finalized"}:
                confirmed_signature = str(item.get("signature") or "")
                if confirmed_signature:
                    break

    if not confirmed_signature:
        return VerifyPaymentResponse(
            ok=False,
            status="pending",
            message="Pagamento ainda não confirmado no bloco.",
            reference=reference,
            wallet_address=wallet_address,
            payment_url=_payment_url(
                recipient=_payment_recipient(),
                amount_sol=order.amount_lamports / 1_000_000_000,
                reference=reference,
                label="Sentinela Digital",
                message="Aguardando confirmação do pagamento",
            ),
        )

    try:
        if not _transaction_matches_order(
            confirmed_signature,
            order_metadata,
            int(order.amount_lamports),
            expected_reference=reference,
        ):
            return VerifyPaymentResponse(
                ok=False,
                status="pending",
                message="A transação não corresponde ao pagador, destinatário e valor desta ordem.",
                reference=reference,
                wallet_address=wallet_address,
            )
    except Exception as exc:
        return VerifyPaymentResponse(
            ok=False,
            status="error",
            message=f"Não foi possível validar os detalhes da transação: {type(exc).__name__}.",
            reference=reference,
            wallet_address=wallet_address,
        )

    user = _user_by_wallet(db, wallet_address)
    if user is None:
        user = User(
            wallet_address=wallet_address,
            auth_method="solana-pay",
            total_credits=0,
            used_scans=0,
        )
        db.add(user)
        db.flush()

    credits_to_add = max(int(order_metadata.get("scans_to_credit") or payload.scans_to_credit or 1), 1)
    user.total_credits += credits_to_add
    db.add(
        ScanCreditLedger(
            user_uuid=user.uuid,
            delta=credits_to_add,
            reason="solana-pay",
            user_metadata=json.dumps(
                {
                    "reference": reference,
                    "signature": confirmed_signature,
                    "wallet_address": wallet_address,
                },
                ensure_ascii=False,
            ),
        )
    )

    order.status = "verified"
    order.user_metadata = json.dumps(
        {
            **order_metadata,
            "reference": reference,
            "wallet_address": wallet_address,
            "confirmed_signature": confirmed_signature,
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
            "credits_added": credits_to_add,
        },
        ensure_ascii=False,
    )
    db.commit()

    target = order_metadata.get("target")
    if isinstance(target, str) and target.strip():
        background_tasks.add_task(_run_paid_solana_scan, target.strip(), reference, confirmed_signature)

    return VerifyPaymentResponse(
        ok=True,
        status="verified",
        message="Pagamento confirmado e créditos atualizados.",
        reference=reference,
        signature=confirmed_signature,
        credits_added=credits_to_add,
        wallet_address=wallet_address,
        payment_url=_payment_url(
            recipient=_payment_recipient(),
            amount_sol=order.amount_lamports / 1_000_000_000,
            reference=reference,
            label="Sentinela Digital",
            message="Pagamento confirmado",
        ),
    )


@router.post("/payments/verify-tx", response_model=VerifyPaymentResponse)
def verify_payment_legacy(
    payload: VerifyPaymentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> VerifyPaymentResponse:
    """Compatibilidade com o endpoint legado."""

    return verify_payment(payload, background_tasks, db)


def _load_wallet_from_order(order: PaymentTransaction | None) -> str | None:
    if order is None or not order.user_metadata:
        return None
    metadata = _safe_json_loads(order.user_metadata)
    wallet_address = metadata.get("wallet_address")
    return wallet_address if isinstance(wallet_address, str) and wallet_address.strip() else None
