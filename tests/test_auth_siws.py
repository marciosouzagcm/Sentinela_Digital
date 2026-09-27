import os
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from nacl.signing import SigningKey

from app.services import siws


def _base58_encode(value: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    zeroes = len(value) - len(value.lstrip(b"\0"))
    number = int.from_bytes(value, "big")
    encoded = ""
    while number:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded
    return "1" * zeroes + encoded


class SiwsAuthenticationTests(unittest.TestCase):
    def setUp(self):
        siws._clear_nonce_store()
        self.signing_key = SigningKey.generate()
        self.public_key = _base58_encode(bytes(self.signing_key.verify_key))
        self.now = datetime(2026, 9, 26, 12, 0, tzinfo=timezone.utc)

    def _challenge_and_signature(self, *, now=None, message_transform=None):
        challenge = siws.issue_siws_challenge(
            self.public_key,
            "sentinela.example",
            "https://sentinela.example/",
            now=now or self.now,
        )
        message = message_transform(challenge.message) if message_transform else challenge.message
        signature = self.signing_key.sign(message.encode("utf-8")).signature.hex()
        return challenge, message, signature

    def test_valid_signature_consumes_nonce_and_issues_jwt(self):
        challenge, message, signature = self._challenge_and_signature()
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes-long"}):
            verified = siws.verify_siws_signature(self.public_key, signature, message, challenge.nonce, now=self.now)
            token, expires_in = siws.create_session_jwt(self.public_key, verified.domain, now=self.now)

        import jwt

        claims = jwt.decode(
            token,
            "test-secret-key-that-is-at-least-32-bytes-long",
            algorithms=["HS256"],
            options={"verify_exp": False},
        )
        self.assertEqual(verified.public_key, self.public_key)
        self.assertEqual(claims["sub"], self.public_key)
        self.assertEqual(claims["iss"], "sentinela.example")
        self.assertEqual(claims["exp"] - claims["iat"], siws.SESSION_TTL_SECONDS)
        self.assertEqual(expires_in, siws.SESSION_TTL_SECONDS)

    def test_invalid_ed25519_signature_is_rejected(self):
        challenge, message, valid_signature = self._challenge_and_signature()
        invalid_signature = bytes(64).hex()

        with self.assertRaises(siws.SiwsInvalidSignature):
            siws.verify_siws_signature(self.public_key, invalid_signature, message, challenge.nonce, now=self.now)
        with self.assertRaises(siws.SiwsNonceUnavailable):
            siws.verify_siws_signature(self.public_key, valid_signature, message, challenge.nonce, now=self.now)

    def test_tampered_message_is_rejected_and_nonce_is_consumed(self):
        challenge, message, signature = self._challenge_and_signature()
        tampered_message = message.replace(siws.SIWS_STATEMENT, "Different statement")

        with self.assertRaises(siws.SiwsMessageMismatch):
            siws.verify_siws_signature(self.public_key, signature, tampered_message, challenge.nonce, now=self.now)
        with self.assertRaises(siws.SiwsNonceUnavailable):
            siws.verify_siws_signature(self.public_key, signature, message, challenge.nonce, now=self.now)

    def test_expired_nonce_is_rejected(self):
        challenge, message, signature = self._challenge_and_signature()
        after_expiry = challenge.expires_at + timedelta(seconds=1)
        siws.issue_siws_challenge(
            self.public_key,
            "sentinela.example",
            "https://sentinela.example/",
            now=after_expiry,
        )

        with self.assertRaises(siws.SiwsNonceExpired):
            siws.verify_siws_signature(self.public_key, signature, message, challenge.nonce, now=after_expiry)

    def test_reused_nonce_is_rejected(self):
        challenge, message, signature = self._challenge_and_signature()
        siws.verify_siws_signature(self.public_key, signature, message, challenge.nonce, now=self.now)

        with self.assertRaises(siws.SiwsNonceUnavailable):
            siws.verify_siws_signature(self.public_key, signature, message, challenge.nonce, now=self.now)

    def test_signature_accepts_base58_encoding(self):
        challenge = siws.issue_siws_challenge(
            self.public_key, "sentinela.example", "https://sentinela.example/", now=self.now
        )
        raw_signature = self.signing_key.sign(challenge.message.encode("utf-8")).signature
        signature_base58 = _base58_encode(raw_signature)

        verified = siws.verify_siws_signature(
            self.public_key, signature_base58, challenge.message, challenge.nonce, now=self.now
        )

        self.assertEqual(verified.nonce, challenge.nonce)

    def test_fastapi_auth_endpoints_reject_invalid_signature_and_replay(self):
        from fastapi.testclient import TestClient

        import main

        class FakeDb:
            def query(self, _model):
                return self

            def filter(self, *_args):
                return self

            def first(self):
                return None

            def add(self, _user):
                pass

            def commit(self):
                pass

            def rollback(self):
                pass

        fake_db = FakeDb()
        original_overrides = dict(main.app.dependency_overrides)
        main.app.dependency_overrides[main.get_db] = lambda: fake_db
        try:
            with patch.dict(os.environ, {
                "SIWS_DOMAIN": "sentinela.example",
                "SIWS_URI": "https://sentinela.example/",
                "JWT_SECRET_KEY": "test-secret-key-that-is-at-least-32-bytes-long",
            }):
                client = TestClient(main.app)
                nonce_response = client.get(
                    "/auth/nonce",
                    params={"public_key": self.public_key},
                )
                self.assertEqual(nonce_response.status_code, 200)
                first_challenge = nonce_response.json()
                invalid_payload = {
                    "public_key": self.public_key,
                    "signature": bytes(64).hex(),
                    "message": first_challenge["message"],
                    "nonce": first_challenge["nonce"],
                }
                self.assertEqual(client.post("/auth/verify-wallet", json=invalid_payload).status_code, 401)

                nonce_response = client.get(
                    "/api/v1/auth/nonce",
                    params={"public_key": self.public_key},
                )
                tampered_challenge = nonce_response.json()
                tampered_message = tampered_challenge["message"].replace(
                    siws.SIWS_STATEMENT,
                    "A different statement.",
                )
                tampered_signature = self.signing_key.sign(tampered_message.encode("utf-8")).signature.hex()
                tampered_payload = {
                    "public_key": self.public_key,
                    "signature": tampered_signature,
                    "message": tampered_message,
                    "nonce": tampered_challenge["nonce"],
                }
                self.assertEqual(client.post("/api/v1/auth/verify-wallet", json=tampered_payload).status_code, 400)

                nonce_response = client.get(
                    "/api/v1/auth/nonce",
                    params={"public_key": self.public_key},
                )
                challenge = nonce_response.json()
                signature = self.signing_key.sign(challenge["message"].encode("utf-8")).signature.hex()
                payload = {
                    "public_key": self.public_key,
                    "signature": signature,
                    "message": challenge["message"],
                    "nonce": challenge["nonce"],
                }
                response = client.post("/api/v1/auth/verify-wallet", json=payload)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["access_token"])
                self.assertEqual(client.post("/api/v1/auth/verify-wallet", json=payload).status_code, 401)

                expired_nonce = siws.issue_siws_challenge(
                    self.public_key,
                    "sentinela.example",
                    "https://sentinela.example/",
                )
                with siws._nonce_lock:
                    siws._nonce_store[expired_nonce.nonce] = replace(
                        expired_nonce,
                        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                    )
                expired_signature = self.signing_key.sign(expired_nonce.message.encode("utf-8")).signature.hex()
                expired_payload = {
                    "public_key": self.public_key,
                    "signature": expired_signature,
                    "message": expired_nonce.message,
                    "nonce": expired_nonce.nonce,
                }
                self.assertEqual(client.post("/api/v1/auth/verify-wallet", json=expired_payload).status_code, 400)
        finally:
            main.app.dependency_overrides.clear()
            main.app.dependency_overrides.update(original_overrides)


if __name__ == "__main__":
    unittest.main()
