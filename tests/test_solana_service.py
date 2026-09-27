import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from app.services import mod_solana


VALID_WALLET = "11111111111111111111111111111111"


class SolanaServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_wallet_balance_converts_lamports_to_sol(self):
        with patch.object(
            mod_solana,
            "_rpc_request",
            new=AsyncMock(return_value=("rpc", {"result": {"value": 1_250_000_000}})),
        ):
            balance = await mod_solana.get_wallet_balance(VALID_WALLET)

        self.assertEqual(balance, 1.25)

    async def test_get_spl_tokens_formats_nonzero_parsed_accounts(self):
        token_account = {
            "pubkey": "token-account",
            "account": {
                "data": {
                    "parsed": {
                        "info": {
                            "mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                            "tokenAmount": {"uiAmount": 12.5, "decimals": 6},
                        }
                    }
                }
            },
        }
        empty_account = {
            "pubkey": "empty-token-account",
            "account": {
                "data": {
                    "parsed": {
                        "info": {
                            "mint": "unknownmint",
                            "tokenAmount": {"uiAmount": 0, "decimals": 9},
                        }
                    }
                }
            },
        }
        rpc = AsyncMock(
            side_effect=[
                ("rpc", {"result": {"value": [token_account, empty_account]}}),
                ("rpc", {"result": {"value": []}}),
            ]
        )
        with patch.object(mod_solana, "_rpc_request", new=rpc):
            tokens = await mod_solana.get_spl_tokens(VALID_WALLET)

        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0]["amount"], 12.5)
        self.assertEqual(tokens[0]["symbol"], "USDC")
        self.assertEqual(rpc.await_count, 2)

    async def test_resolve_sns_domain_uses_configured_static_map(self):
        with patch.dict(os.environ, {"SOLANA_SNS_STATIC_MAP_JSON": json.dumps({"alice.sol": VALID_WALLET})}):
            resolved = await mod_solana.resolve_sns_domain("Alice.SOL")

        self.assertEqual(resolved, VALID_WALLET)
        self.assertEqual(await mod_solana.resolve_sns_domain(VALID_WALLET), VALID_WALLET)

    async def test_sanctions_are_critical_and_flagged_addresses_are_high(self):
        with patch.dict(
            os.environ,
            {
                "SOLANA_SANCTIONED_ADDRESSES_JSON": json.dumps([VALID_WALLET]),
                "SOLANA_FLAGGED_ADDRESSES_JSON": "{}",
            },
        ):
            result = await mod_solana.check_sanctions_and_flags(VALID_WALLET)

        self.assertTrue(result["sanctioned"])
        self.assertTrue(result["flagged"])
        self.assertEqual(result["risk_level"], "critical")
        self.assertEqual(result["risk_score"], 100)

    async def test_rpc_failures_return_safe_fallback_values(self):
        with patch.object(mod_solana, "_rpc_request", new=AsyncMock(side_effect=TimeoutError("rpc timeout"))):
            balance = await mod_solana.get_wallet_balance(VALID_WALLET)
            tokens = await mod_solana.get_spl_tokens(VALID_WALLET)

        self.assertEqual(balance, 0.0)
        self.assertEqual(tokens, [])

    async def test_scan_returns_partial_structured_result_if_rpc_fails(self):
        with (
            patch.object(mod_solana, "check_sanctions_and_flags", new=AsyncMock(return_value={"flags": [], "flagged": False})),
            patch.object(mod_solana, "_get_wallet_balance_result", new=AsyncMock(return_value=(None, "balance: TimeoutError"))),
            patch.object(mod_solana, "_get_spl_tokens_result", new=AsyncMock(return_value=([], ["tokens: TimeoutError"]))),
            patch.object(mod_solana, "_rpc_request", new=AsyncMock(side_effect=TimeoutError("rpc timeout"))),
        ):
            result = await mod_solana.scan_solana_target(VALID_WALLET)

        self.assertEqual(result["status"], "partial")
        self.assertIsNone(result["data"]["result"]["sol_balance"])
        self.assertEqual(result["data"]["result"]["token_accounts"], [])
        self.assertTrue(result["data"]["result"]["errors"])


if __name__ == "__main__":
    unittest.main()