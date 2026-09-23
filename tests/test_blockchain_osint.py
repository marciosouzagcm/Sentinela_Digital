from pathlib import Path

from modules.osint import mod_blockchain


def test_invalid_wallet_is_rejected_without_network_call(tmp_path):
    result = mod_blockchain.analisar_carteira_evm("not-a-wallet", tmp_path)

    assert result["status"] == "unavailable"
    assert "inválido" in result["data"]["error"]


def test_blockchain_email_correlation_is_explicitly_non_deterministic(tmp_path):
    result = mod_blockchain.run_blockchain("user@example.com", Path(tmp_path))

    assert result["status"] == "warning"
    assert result["data"]["web3_domains"] == []
    assert "associação" in result["data"]["warning"]


def test_blockchain_wallet_maps_public_api_payload(monkeypatch, tmp_path):
    address = "0x" + "1" * 40
    monkeypatch.setattr(
        mod_blockchain,
        "_get_json",
        lambda url: (200, {"data": {address: {"address": {
            "balance": 2_000_000_000_000_000_000,
            "transaction_count": 4,
            "first_seen_receiving": "2024-01-01",
            "last_seen_receiving": "2024-02-01",
            "calls_count": 2,
        }}}}),
    )

    result = mod_blockchain.analisar_carteira_evm(address, tmp_path)

    assert result["status"] == "success"
    assert result["data"]["balance_eth"] == 2
    assert result["data"]["transaction_count"] == 4
    assert (tmp_path / "blockchain.json").exists()


def test_correlated_wallet_is_marked_as_passive_hypothesis(monkeypatch, tmp_path):
    address = "0x" + "2" * 40
    monkeypatch.setattr(
        mod_blockchain,
        "analisar_carteira_evm",
        lambda wallet, output_dir: {"status": "success", "output_file": None, "data": {}},
    )

    result = mod_blockchain.run_blockchain("user@example.com", tmp_path, address)

    assert "passiva" in result["data"]["correlacao_nota"]
    assert "não comprova propriedade" in result["data"]["correlacao_nota"]