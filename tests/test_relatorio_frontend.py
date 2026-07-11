import json
import unittest
from pathlib import Path

from modulos.gestao import gerar_relatorio
from modulos.utilidades import Vulnerabilidade


class RelatorioFrontendTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]
        self.frontend_file = self.root / "public" / "relatorios" / "ultimo_relatorio.json"
        self.report_dir = self.root / "relatorios"

        for path in self.frontend_file.parent.glob("ultimo_relatorio.json"):
            path.unlink(missing_ok=True)
        for path in self.report_dir.glob("relatorio_*.json"):
            path.unlink(missing_ok=True)
        for path in self.report_dir.glob("relatorio_*.txt"):
            path.unlink(missing_ok=True)

    def test_gerar_relatorio_atualiza_arquivo_para_o_frontend(self):
        vulnerabilidade = Vulnerabilidade(
            identificador="A02-HDR-Strict-Transport-Security",
            categoria="A02",
            titulo="Sem HSTS",
            descricao="Cabeçalho HTTP 'Strict-Transport-Security' não está presente.",
            ativo="https://google.com",
            severidade="ALTA",
            evidencia="Cabeçalhos recebidos",
            mitigacao="Adicionar Strict-Transport-Security.",
        )

        gerar_relatorio([vulnerabilidade], "https://google.com")

        self.assertTrue(self.frontend_file.exists(), "O arquivo do frontend não foi atualizado")
        with self.frontend_file.open("r", encoding="utf-8") as handle:
            dados = json.load(handle)

        self.assertEqual(dados["alvo"], "https://google.com")
        self.assertEqual(dados["metricas"]["ALTA"], 1)
        self.assertEqual(dados["metricas"]["TOTAL"], 1)


if __name__ == "__main__":
    unittest.main()
