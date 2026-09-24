from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class User(Base):
    """Represents a wallet-backed user account for Web3 authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    wallet: Mapped[str | None] = mapped_column(String(88), nullable=True, index=True)
    auth_method: Mapped[str] = mapped_column(String(32), default="siws")
    total_credits: Mapped[int] = mapped_column(Integer, default=0)
    used_scans: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    metadata: Mapped[str | None] = mapped_column(Text, nullable=True)


class PaymentTransaction(Base):
    """Stores verified Solana payment metadata for audit and accounting."""

    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_uuid: Mapped[str] = mapped_column(String(64), index=True)
    signature: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    amount_lamports: Mapped[int] = mapped_column(Integer, default=0)
    token_mint: Mapped[str | None] = mapped_column(String(88), nullable=True)
    currency: Mapped[str] = mapped_column(String(16), default="SOL")
    status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScanCreditLedger(Base):
    """Tracks credit balance and scan-history adjustments."""

    __tablename__ = "scan_credit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_uuid: Mapped[str] = mapped_column(String(64), index=True)
    delta: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(String(64), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata: Mapped[str | None] = mapped_column(Text, nullable=True)
