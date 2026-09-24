"""API routes for wallet authentication and Solana payment verification."""

from .database import get_db
from .solana_pay import router

__all__ = ["router", "get_db"]
