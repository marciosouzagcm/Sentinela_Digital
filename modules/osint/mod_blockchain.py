"""Adaptador de OSINT público para endereços EVM e correlação Web3."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("sentinela")
EVM_ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
WEB3_DOMAIN_RE = re.compile(r"(?i)(?:[a-z0-9-]+\.)+(?:eth|crypto|nft|wallet)\b")


def _get_json(url: str, timeout: int = 10) -> tuple[int, dict[str, Any]]:
    request = Request(url, headers={"User-Agent": "Sentinela-Digital/1.0"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return int(response.status), payload if isinstance(payload, dict) else {}


def _resultado(status: str, data: dict[str, Any], output_file: Path | None = None) -> dict[str, Any]:
    return {"status": status, "output_file": str(output_file) if output_file else None, "data": data}


def analisar_carteira_evm(wallet_address: str, output_dir: str | Path | None = None) -> dict[str, Any]:
    """Coleta saldo e telemetria pública de um endereço EVM via Blockchair."""
    if not EVM_ADDRESS_RE.fullmatch((wallet_address or "").strip()):
        return _resultado("unavailable", {"error": "Endereço de carteira EVM inválido ou não fornecido."})

    address = wallet_address.strip()
    output_file = Path(output_dir) / "blockchain.json" if output_dir else None
    url = f"https://api.blockchair.com/ethereum/dashboards/address/{address}"
    try:
        status_code, raw_data = _get_json(url)
        if status_code == 429:
            return _resultado("rate_limited", {"error": "Limite de requisições atingido na API de blockchain."}, output_file)
        address_info = (raw_data.get("data") or {}).get(address, {}).get("address") or {}
        if status_code != 200 or not address_info:
            return _resultado("warning", {"error": f"API retornou status HTTP {status_code} ou dados vazios."}, output_file)
        payload = {
            "wallet": address,
            "chain": "ethereum",
            "balance_eth": address_info.get("balance") / 1e18 if isinstance(address_info.get("balance"), (int, float)) else None,
            "transaction_count": address_info.get("transaction_count", 0),
            "first_seen": address_info.get("first_seen_receiving"),
            "last_seen": address_info.get("last_seen_receiving"),
            "smart_contract_interactions": address_info.get("calls_count", 0),
            "ens_domain": None,
            "flags_sanction": False,
            "reputation": {"status": "not_checked", "reason": "Fonte pública de reputação requer credencial/configuração."},
        }
        result = _resultado("success", payload, output_file)
    except HTTPError as exc:
        status = "rate_limited" if exc.code == 429 else "warning"
        result = _resultado(status, {"error": f"API de blockchain retornou HTTP {exc.code}."}, output_file)
    except (TimeoutError, URLError, ValueError, json.JSONDecodeError) as exc:
        result = _resultado("error", {"error": f"Falha na consulta pública de blockchain: {exc}"}, output_file)
    except OSError as exc:
        result = _resultado("error", {"error": f"Falha de rede na consulta de blockchain: {exc}"}, output_file)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(result["data"], indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def run_blockchain(target: str, output_dir: Path, wallet: str | None = None) -> dict[str, Any]:
    """Executa análise de carteira ou correlação não-invasiva por e-mail."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if wallet:
        resultado = analisar_carteira_evm(wallet, output_dir)
        resultado.setdefault("data", {})["correlacao_nota"] = (
            "Endereço fornecido via flag de correlação investigativa passiva; "
            "a relação com o e-mail não comprova propriedade."
        )
        return resultado
    matches = WEB3_DOMAIN_RE.findall(target or "")
    message = "Nenhuma associação Web3 determinística foi encontrada no identificador fornecido."
    data: dict[str, Any] = {"email": target, "web3_domains": sorted(set(matches)), "warning": message}
    if matches:
        data["warning"] = "Domínio Web3 identificado; a associação com uma carteira exige validação adicional autorizada."
    return _resultado("warning", data)