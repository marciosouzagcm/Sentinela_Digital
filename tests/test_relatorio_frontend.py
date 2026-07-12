import json
import os
import unittest
from pathlib import Path

from modulos.gestao import gerar_relatorio, obter_ultimo_relatorio, _obter_configuracao_tidb
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

    def test_obter_ultimo_relatorio_faz_fallback_para_arquivo_local(self):
        vulnerabilidade = Vulnerabilidade(
            identificador="A05-Security-Misconfiguration",
            categoria="A05",
            titulo="Configuração insegura",
            descricao="Configuração insegura detectada.",
            ativo="https://example.com",
            severidade="MEDIA",
            evidencia="Configuração",
            mitigacao="Corrigir configuração.",
        )

        gerar_relatorio([vulnerabilidade], "https://example.com")
        dados = obter_ultimo_relatorio()

        self.assertIsNotNone(dados)
        self.assertEqual(dados["alvo"], "https://example.com")
        self.assertEqual(dados["metricas"]["MEDIA"], 1)

    def test_obter_configuracao_tidb_a_partir_de_url_completa(self):
        os.environ["TIDB_URL"] = "mysql://usuario:senha@gateway01.us-east-1.prod.aws.tidbcloud.com:4000/sentinela"
        os.environ["TIDB_USER"] = ""
        os.environ["TIDB_PASSWORD"] = ""
        os.environ["TIDB_DATABASE"] = ""

        configuracao = _obter_configuracao_tidb()

        self.assertEqual(configuracao["host"], "gateway01.us-east-1.prod.aws.tidbcloud.com")
        self.assertEqual(configuracao["port"], 4000)
        self.assertEqual(configuracao["user"], "usuario")
        self.assertEqual(configuracao["password"], "senha")
        self.assertEqual(configuracao["database"], "sentinela")

    def test_obter_configuracao_tidb_usa_variaveis_explicitas_e_decodifica_senha(self):
        os.environ["TIDB_URL"] = "mysql://usuario_url:p%40ss%3Aword@gateway01.us-east-1.prod.aws.tidbcloud.com:4000/db_url"
        os.environ["TIDB_USER"] = "usuario_explicit"
        os.environ["TIDB_PASSWORD"] = "senha_explicit"
        os.environ["TIDB_DATABASE"] = "db_explicit"

        configuracao = _obter_configuracao_tidb()

        self.assertEqual(configuracao["user"], "usuario_explicit")
        self.assertEqual(configuracao["password"], "senha_explicit")
        self.assertEqual(configuracao["database"], "db_explicit")
        self.assertEqual(configuracao["host"], "gateway01.us-east-1.prod.aws.tidbcloud.com")


if __name__ == "__main__":
    unittest.main()
