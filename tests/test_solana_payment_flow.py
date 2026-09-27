import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import BackgroundTasks

from app.api import solana_pay


WALLET = "11111111111111111111111111111111"
TREASURY = "Vote111111111111111111111111111111111111111"


class SolanaPaymentFlowTests(unittest.TestCase):
    def test_create_order_accepts_email_web_and_solana_targets(self):
        targets = [
            "user@example.com",
            "https://example.com/audit",
            "example.com",
            "alice.sol",
            WALLET,
        ]

        for target in targets:
            with self.subTest(target=target):
                db = MagicMock()
                with (
                    patch.object(solana_pay, "_payment_recipient", return_value=TREASURY),
                    patch.object(solana_pay, "_make_reference", return_value=WALLET),
                ):
                    response = solana_pay.create_order(
                        solana_pay.CreateOrderRequest(wallet_address=WALLET, target=target),
                        db,
                    )

                stored_order = db.add.call_args.args[0]
                stored_metadata = json.loads(stored_order.user_metadata)
                self.assertEqual(stored_metadata["target"], target)
                self.assertEqual(response.payment_url.split(":", 1)[0], "solana")
                db.commit.assert_called_once()

    def test_create_order_trims_target_and_rejects_blank_target(self):
        db = MagicMock()
        with (
            patch.object(solana_pay, "_payment_recipient", return_value=TREASURY),
            patch.object(solana_pay, "_make_reference", return_value=WALLET),
        ):
            response = solana_pay.create_order(
                solana_pay.CreateOrderRequest(wallet_address=WALLET, target="  user@example.com  "),
                db,
            )
        self.assertEqual(json.loads(db.add.call_args.args[0].user_metadata)["target"], "user@example.com")

        with self.assertRaises(Exception) as raised:
            solana_pay.create_order(
                solana_pay.CreateOrderRequest(wallet_address=WALLET, target="   "),
                MagicMock(),
            )
        self.assertEqual(getattr(raised.exception, "status_code", None), 422)

    def test_rpc_urls_follow_selected_cluster_and_keep_public_fallback(self):
        with patch.dict(os.environ, {
            "SOLANA_ENV": "devnet",
            "SOLANA_RPC_URLS": "https://rpc-one.example,https://rpc-two.example",
        }):
            self.assertEqual(
                solana_pay._rpc_urls(),
                [
                    "https://rpc-one.example",
                    "https://rpc-two.example",
                    "https://api.devnet.solana.com",
                ],
            )

        with patch.dict(os.environ, {"SOLANA_ENV": "mainnet-beta", "SOLANA_RPC_URLS": ""}):
            self.assertEqual(solana_pay._rpc_urls(), ["https://api.mainnet-beta.solana.com"])

        with patch.dict(os.environ, {"SOLANA_ENV": "invalid-cluster", "SOLANA_RPC_URLS": ""}):
            with self.assertRaises(ValueError):
                solana_pay._rpc_urls()

    def test_transaction_matches_persisted_payee_amount_and_signer(self):
        metadata = {"recipient": TREASURY, "wallet_address": WALLET}
        reference = "So11111111111111111111111111111111111111112"
        rpc_payload = {
            "result": {
                "transaction": {
                    "message": {
                        "accountKeys": [
                            {"pubkey": WALLET, "signer": True},
                            {"pubkey": reference, "signer": False},
                        ],
                        "instructions": [{
                            "program": "system",
                            "parsed": {"type": "transfer", "info": {"destination": TREASURY, "lamports": 75}},
                        }],
                    },
                    "meta": {"err": None},
                }
            }
        }
        with patch.object(solana_pay, "_rpc_request", return_value=rpc_payload):
            self.assertTrue(solana_pay._transaction_matches_order("signature", metadata, 50, reference))
            self.assertFalse(solana_pay._transaction_matches_order("signature", metadata, 50, TREASURY))
            self.assertFalse(solana_pay._transaction_matches_order("signature", metadata, 100, reference))
            self.assertFalse(solana_pay._transaction_matches_order(
                "signature", {**metadata, "wallet_address": reference}, 50, reference
            ))

    def test_repeated_verified_payment_is_idempotent(self):
        metadata = {
            "wallet_address": WALLET,
            "payment_url": "solana:treasury?reference=reference",
            "confirmed_signature": "confirmed-signature",
            "credits_added": 3,
        }
        order = SimpleNamespace(status="verified", user_metadata=json.dumps(metadata))
        background_tasks = BackgroundTasks()
        with patch.object(solana_pay, "_order_by_reference", return_value=order):
            response = solana_pay.verify_payment(
                solana_pay.VerifyPaymentRequest(reference=WALLET, wallet_address=WALLET),
                background_tasks,
                MagicMock(),
            )

        self.assertEqual(response.status, "verified")
        self.assertEqual(response.credits_added, 3)
        self.assertEqual(background_tasks.tasks, [])

    def test_confirmed_payment_schedules_scan_using_persisted_order_values(self):
        metadata = {
            "reference": WALLET,
            "wallet_address": WALLET,
            "target": "alice.sol",
            "recipient": TREASURY,
            "amount_sol": 0.05,
            "scans_to_credit": 5,
        }
        order = SimpleNamespace(
            status="pending",
            user_metadata=json.dumps(metadata),
            amount_lamports=50_000_000,
        )
        user = SimpleNamespace(uuid="user-uuid", total_credits=0)
        db = MagicMock()
        background_tasks = BackgroundTasks()
        with (
            patch.dict(os.environ, {"SOLANA_TREASURY_WALLET": TREASURY}),
            patch.object(solana_pay, "_order_by_reference", return_value=order),
            patch.object(solana_pay, "_signatures_for_reference", return_value=[{
                "signature": "confirmed-signature", "confirmationStatus": "confirmed", "err": None,
            }]),
            patch.object(solana_pay, "_transaction_matches_order", return_value=True),
            patch.object(solana_pay, "_user_by_wallet", return_value=user),
        ):
            response = solana_pay.verify_payment(
                solana_pay.VerifyPaymentRequest(
                    reference=WALLET,
                    wallet_address=WALLET,
                    scans_to_credit=1,
                    expected_amount_sol=0.000000001,
                ),
                background_tasks,
                db,
            )

        self.assertEqual(response.status, "verified")
        self.assertEqual(response.credits_added, 5)
        self.assertEqual(user.total_credits, 5)
        self.assertEqual(len(background_tasks.tasks), 1)
        self.assertEqual(background_tasks.tasks[0].args, ("alice.sol", WALLET, "confirmed-signature"))
        self.assertEqual(order.status, "verified")

    def test_verify_tx_uses_direct_signature_only_after_rpc_confirmation(self):
        metadata = {
            "wallet_address": WALLET,
            "target": "user@example.com",
            "recipient": TREASURY,
            "scans_to_credit": 1,
        }
        order = SimpleNamespace(status="pending", user_metadata=json.dumps(metadata), amount_lamports=50_000_000)
        pending_payload = solana_pay.VerifyPaymentRequest.model_validate({
            "reference": WALLET,
            "txSignature": "some-transaction-signature",
            "wallet_address": WALLET,
        })

        with (
            patch.object(solana_pay, "_order_by_reference", return_value=order),
            patch.object(solana_pay, "_signature_is_confirmed", return_value=False),
            patch.object(solana_pay, "_signatures_for_reference", side_effect=AssertionError("must use provided txSignature")),
        ):
            pending = solana_pay.verify_payment(pending_payload, BackgroundTasks(), MagicMock())
        self.assertEqual(pending.status, "pending")

        user = SimpleNamespace(uuid="user-uuid", total_credits=0)
        db = MagicMock()
        with (
            patch.object(solana_pay, "_order_by_reference", return_value=order),
            patch.object(solana_pay, "_signature_is_confirmed", return_value=True),
            patch.object(solana_pay, "_transaction_matches_order", return_value=True),
            patch.object(solana_pay, "_signatures_for_reference", side_effect=AssertionError("must use provided txSignature")),
            patch.object(solana_pay, "_user_by_wallet", return_value=user),
        ):
            verified = solana_pay.verify_payment(pending_payload, BackgroundTasks(), db)

        self.assertEqual(verified.status, "verified")
        self.assertEqual(verified.signature, "some-transaction-signature")
        self.assertEqual(verified.credits_added, 1)

    def test_verify_tx_accepts_camel_case_tx_signature_and_confirms_on_chain(self):
        metadata = {
            "wallet_address": WALLET,
            "target": "user@example.com",
            "recipient": TREASURY,
            "payment_url": "solana:treasury",
            "scans_to_credit": 2,
        }
        order = SimpleNamespace(status="pending", user_metadata=json.dumps(metadata), amount_lamports=50_000_000)
        user = SimpleNamespace(uuid="user-uuid", total_credits=0)
        db = MagicMock()
        background_tasks = BackgroundTasks()
        payload = solana_pay.VerifyPaymentRequest.model_validate({
            "reference": WALLET,
            "txSignature": "confirmed-transaction-signature",
            "wallet_address": WALLET,
        })

        with (
            patch.object(solana_pay, "_order_by_reference", return_value=order),
            patch.object(solana_pay, "_signature_is_confirmed", return_value=True) as check_status,
            patch.object(solana_pay, "_transaction_matches_order", return_value=True) as check_transaction,
            patch.object(solana_pay, "_signatures_for_reference", side_effect=AssertionError("reference scan should be skipped")),
            patch.object(solana_pay, "_user_by_wallet", return_value=user),
        ):
            response = solana_pay.verify_payment(payload, background_tasks, db)

        self.assertEqual(response.status, "verified")
        self.assertEqual(response.signature, "confirmed-transaction-signature")
        self.assertEqual(response.credits_added, 2)
        check_status.assert_called_once_with("confirmed-transaction-signature")
        check_transaction.assert_called_once_with(
            "confirmed-transaction-signature", metadata, 50_000_000, expected_reference=WALLET
        )


if __name__ == "__main__":
    unittest.main()
