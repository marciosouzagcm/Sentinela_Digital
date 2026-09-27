import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.services import solana_reporting
from pdf_generator import parse_solana


class SolanaReportingTests(unittest.IsolatedAsyncioTestCase):
    def test_pdf_parser_keeps_risk_score_and_partial_errors(self):
        parsed = parse_solana({
            "status": "partial",
            "data": {"result": {
                "risk": {"risk_level": "high", "risk_score": 75, "flags": [{"label": "local list"}]},
                "errors": ["balance: TimeoutException"],
            }},
        })

        self.assertEqual(parsed["risk"]["risk_score"], 75)
        self.assertEqual(parsed["flags"][0]["label"], "local list")
        self.assertEqual(parsed["errors"], ["balance: TimeoutException"])

    async def test_report_preserves_dashboard_contract_and_onchain_pdf_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            history_dir = root / "history"
            public_dir = root / "public"
            output_dir = root / "master"
            history_dir.mkdir()
            public_dir.mkdir()
            output_dir.mkdir()
            scan_data = {
                "target": "risk.sol",
                "target_type": "domain",
                "wallet_address": "11111111111111111111111111111111",
                "sol_balance": 0.75,
                "token_accounts": [{"mint": "mint", "symbol": "TOK", "amount": 4}],
                "sns": {"requested": "risk.sol", "resolved_address": "11111111111111111111111111111111", "status": "resolved_static"},
                "flags": [{"label": "local high risk", "risk_level": "high"}],
                "risk": {"flags": [{"label": "local high risk", "risk_level": "high"}]},
                "errors": [],
            }
            frontend_file = public_dir / "ultimo_relatorio.json"
            json_file = history_dir / "report.json"

            def save_report(findings, target, metadata):
                metrics = {
                    "TOTAL": len(findings),
                    "CRITICA": sum(item.severidade == "CRITICA" for item in findings),
                    "ALTA": sum(item.severidade == "ALTA" for item in findings),
                    "MEDIA": sum(item.severidade == "MEDIA" for item in findings),
                    "BAIXA": sum(item.severidade == "BAIXA" for item in findings),
                }
                payload = {
                    "alvo": target,
                    "gerado_em": "2026-09-26T00:00:00+00:00",
                    "metricas": metrics,
                    "categorias": {"SOLANA-RISK": [item.para_dict() for item in findings]},
                    **metadata,
                }
                encoded = json.dumps(payload, ensure_ascii=False)
                json_file.write_text(encoded, encoding="utf-8")
                frontend_file.write_text(encoded, encoding="utf-8")
                return {"json": str(json_file), "frontend": str(frontend_file)}

            with (
                patch.object(solana_reporting, "scan_solana_target", new=AsyncMock(return_value={
                    "status": "success", "output_file": None, "data": {"result": scan_data}
                })),
                patch.object(solana_reporting, "gerar_relatorio", side_effect=save_report),
            ):
                report = await solana_reporting.generate_solana_report(
                    "risk.sol",
                    payment={"reference": "reference", "signature": "signature"},
                    output_dir=output_dir,
                )

            self.assertEqual(report["alvo"], "risk.sol")
            self.assertEqual(report["metricas"]["TOTAL"], 1)
            self.assertEqual(report["metricas"]["ALTA"], 1)
            self.assertEqual(report["solana"]["sol_balance"], 0.75)
            self.assertEqual(report["ferramentas"]["solana"]["data"]["result"]["token_accounts"][0]["symbol"], "TOK")
            self.assertEqual(report["payment"]["status"], "verified")
            self.assertEqual(report["pdf"], str(output_dir / "report.pdf"))
            self.assertTrue(Path(report["pdf"]).exists())
            self.assertTrue(frontend_file.exists())
            self.assertEqual(json.loads(frontend_file.read_text(encoding="utf-8"))["metricas"]["TOTAL"], 1)


if __name__ == "__main__":
    unittest.main()
