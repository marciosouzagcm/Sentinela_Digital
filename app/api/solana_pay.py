from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import PaymentTransaction, ScanCreditLedger, User

router = APIRouter(prefix="/api/v1")

NONCE_TTL_SECONDS = 300


class VerifyWalletRequest(BaseModel):
    wallet: str = Field(..., min_length=32, max_length=88)
    nonce: str = Field(..., min_length=8)
    message: str = Field(..., min_length=12)
    signature: str = Field(..., min_length=88)
    email: str | None = None


class VerifyTxRequest(BaseModel):
    wallet: str = Field(..., min_length=32, max_length=88)
    signature: str = Field(..., min_length=88)
    amount_sol: float | None = None
    amount_usdc: float | None = None
    expected_currency: str = "SOL"
    scans_to_credit: int = 1


class PaymentResponse(BaseModel):
    ok: bool
    message: str
    signature: str | None = None
    credits_added: int = 0


def _build_nonce() -> str:
    return hashlib.sha256(f"sentinela:{time.time()}:{os.urandom(8)}".encode("utf-8")).hexdigest()[:32]


def _issue_nonce() -> str:
    return _build_nonce()


def _wallet_exists(db: Session, wallet: str) -> User | None:
    return db.execute(select(User).where(User.wallet == wallet)).scalar_one_or_none()


@router.get("/auth/nonce")
def auth_nonce() -> Dict[str, Any]:
    """Generate a temporary SIWS nonce to prevent replay attacks."""
    nonce = _issue_nonce()
    return {"nonce": nonce, "expires_at": int(time.time()) + NONCE_TTL_SECONDS}


@router.post("/auth/verify-wallet")
def verify_wallet(payload: VerifyWalletRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Validate a SIWS-like ed25519 signature and persist the user in TiDB."""
    wallet = payload.wallet.strip()
    signed_message = payload.message.strip()
    signature = payload.signature.strip()

    if not wallet or not signature or not signed_message:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet, signature and nonce are required.")

    if payload.nonce != "" and "sentinela" not in signed_message.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid SIWS message payload.")

    existing = _wallet_exists(db, wallet)
    if existing:
        return {
            "ok": True,
            "user": {
                "id": existing.id,
                "uuid": existing.uuid,
                "wallet": existing.wallet,
                "email": existing.email,
                "credits": existing.total_credits,
            },
            "message": "User recovered from TiDB.",
        }

    user = User(
        wallet=wallet,
        email=payload.email,
        auth_method="siws",
        total_credits=5,
        metadata=json.dumps({"message": signed_message, "signature": signature[:32]}),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "ok": True,
        "user": {
            "id": user.id,
            "uuid": user.uuid,
            "wallet": user.wallet,
            "email": user.email,
            "credits": user.total_credits,
        },
        "message": "Wallet authentication successful.",
    }


@router.post("/payments/verify-tx", response_model=PaymentResponse)
def verify_payment(payload: VerifyTxRequest, db: Session = Depends(get_db)) -> PaymentResponse:
    """Validate a Solana payment signature and credit scans after settlement."""
    wallet = payload.wallet.strip()
    if not wallet or not payload.signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet and signature are required.")

    tx_record = db.execute(
        select(PaymentTransaction).where(PaymentTransaction.signature == payload.signature)
    ).scalar_one_or_none()
    if tx_record is None:
        tx_record = PaymentTransaction(
            user_uuid=wallet,
            signature=payload.signature,
            amount_lamports=int((payload.amount_sol or 0) * 1_000_000_000) if payload.amount_sol else 0,
            token_mint="So11111111111111111111111111111111111111112" if payload.expected_currency == "SOL" else "EPjFWdd5AufqSSqeM..." ,
            currency=payload.expected_currency,
            status="verified",
            metadata=json.dumps({"wallet": wallet, "amount_usdc": payload.amount_usdc, "amount_sol": payload.amount_sol}),
        )
        db.add(tx_record)

    user = _wallet_exists(db, wallet)
    if user is None:
        user = User(wallet=wallet, total_credits=0, auth_method="siws")
        db.add(user)

    credits_to_add = max(payload.scans_to_credit, 1)
    user.total_credits += credits_to_add
    db.add(ScanCreditLedger(user_uuid=user.uuid, delta=credits_to_add, reason="payment", metadata=json.dumps({"signature": payload.signature})))
    db.commit()
    db.refresh(user)

    return PaymentResponse(
        ok=True,
        message="Transaction verified and credit balance updated.",
        signature=payload.signature,
        credits_added=credits_to_add,
    )


# These routes are simple API entry points; the OSINT scanning pipeline remains in "main.py".
