from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from app.services.mod_solana import scan_solana_target
from modulos.gestao import gerar_relatorio
from modulos.utilidades import Vulnerabilidade
from pdf_generator import gerar_pdf

logger = logging.getLogger("sentinela")

_SEVERITY_BY_RISK = {
    "critical": "CRITICA",
    "critica": "CRITICA",
    "high": "ALTA",
    "alta": "ALTA",
    "medium": "MEDIA",
    "media": "MEDIA",
    "low": "BAIXA",
    "baixa": "BAIXA",
}


def _risk_findings(scan_data: dict[str, Any]) -> list[Vulnerabilidade]:
    address = scan_data.get("wallet_address") or scan_data.get("target") or "Solana"
    findings: list[Vulnerabilidade] = []
    risk = scan_data.get("risk") or {}
    flags = risk.get("flags") or scan_data.get("flags") or []
    for index, flag in enumerate(flags, start=1):
        if not isinstance(flag, dict):
            continue
        level = str(flag.get("risk_level") or flag.get("severity") or "").lower()
        if flag.get("sanctioned"):
            level = "critical"
        severity = _SEVERITY_BY_RISK.get(level, "ALTA")
        label = flag.get("label") or flag.get("name") or flag.get("source") or "Lista local de risco"
        findings.append(
            Vulnerabilidade(
                identificador=f"SOL-FLAG-{index:03d}",
                categoria="SOLANA-RISK",
                titulo="Carteira sinalizada em lista local",
                descricao=(
                    f"O endereço foi identificado por uma regra local ({label}). "
                    "Valide a fonte e o contexto antes de qualquer decisão."
                ),
                ativo=str(address),
                severidade=severity,
                evidencia=json.dumps(flag, ensure_ascii=False, sort_keys=True),
                mitigacao=(
                    "Trate o resultado como alerta preliminar; valide a fonte da lista e "
                    "aplique os procedimentos de compliance da organização."
                ),
            )
        )
    return findings


async def generate_solana_report(
    target: str,
    *,
    payment: dict[str, str] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Run on-chain enrichment and publish dashboard JSON plus an executive PDF."""
    scan = await scan_solana_target(target, output_dir)
    scan_data = (scan.get("data") or {}).get("result") or {}
    findings = _risk_findings(scan_data)

    master_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parents[2] / "reports"
    master_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "solana": scan_data,
        "solana_scan": {
            "status": scan.get("status", "unknown"),
            "partial": scan.get("status") == "partial",
            "errors": scan_data.get("errors", []),
        },
        "ferramentas": {
            "solana": {
                "status": scan.get("status", "unknown"),
                "output_file": scan.get("output_file"),
                "data": scan.get("data") or {},
            }
        },
    }
    if payment:
        metadata["payment"] = {
            "status": "verified",
            "reference": payment.get("reference"),
            "signature": payment.get("signature"),
        }

    report_paths = await asyncio.to_thread(gerar_relatorio, findings, target, metadata)
    json_path = Path(report_paths["json"])
    pdf_path = master_dir / f"{json_path.stem}.pdf"
    try:
        await asyncio.to_thread(gerar_pdf, json_path, pdf_path)
        report = json.loads(json_path.read_text(encoding="utf-8"))
        report["pdf"] = str(pdf_path)
        report["relatorio_mestre"] = str(json_path)
        serialized = json.dumps(report, ensure_ascii=False, indent=2)
        json_path.write_text(serialized, encoding="utf-8")
        Path(report_paths["frontend"]).write_text(serialized, encoding="utf-8")
    except Exception as exc:
        logger.exception("Falha ao gerar ou atualizar o PDF da análise Solana.")
        report = json.loads(json_path.read_text(encoding="utf-8"))
        report["pdf_error"] = type(exc).__name__
        report["relatorio_mestre"] = str(json_path)
        serialized = json.dumps(report, ensure_ascii=False, indent=2)
        json_path.write_text(serialized, encoding="utf-8")
        Path(report_paths["frontend"]).write_text(serialized, encoding="utf-8")

    return report
