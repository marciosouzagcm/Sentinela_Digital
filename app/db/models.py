from __future__ import annotations

import uuid
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class User(Base):
    """Represents a wallet-backed user account for Web3 authentication."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uuid: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    wallet_address: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    auth_method: Mapped[str] = mapped_column(String(32), default="siws")
    total_credits: Mapped[int] = mapped_column(Integer, default=0)
    used_scans: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_metadata: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)


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
    user_metadata: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    SCAN_IN_PROGRESS = "SCAN_IN_PROGRESS"
    COMPLETED = "COMPLETED"


class Payment(Base):
    """Tracks the idempotent post-payment scan and report lifecycle."""

    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_wallet: Mapped[str] = mapped_column(String(44), nullable=False, index=True)
    tx_signature: Mapped[str | None] = mapped_column(String(88), unique=True, nullable=True, index=True)
    reference_key: Mapped[str] = mapped_column(String(44), unique=True, nullable=False, index=True)
    target_host: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_sol: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False
    )
    pdf_report_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ScanCreditLedger(Base):
    """Tracks credit balance and scan-history adjustments."""

    __tablename__ = "scan_credit_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_uuid: Mapped[str] = mapped_column(String(64), index=True)
    delta: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(String(64), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_metadata: Mapped[str | None] = mapped_column("metadata", Text, nullable=True)
