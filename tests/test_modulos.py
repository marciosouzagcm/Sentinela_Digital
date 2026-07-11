import json
import os
import sys
import types
from pathlib import Path

import pytest

from modulos.gestao import gerar_relatorio, reavaliar, priorizar
from modulos.utilidades import Vulnerabilidade
from modulos.coleta import coletar_informacoes
from modulos.escaneamento import escanear, _scan_socket
from modulos.analise_codigo import analisar_diretorio
from modulos.pentest import pentest_web
from modulos.sca import analisar_dependencias
import main as main_module


class FakeResponse:
    def __init__(self, status_code=200, headers=None, content=b"ok", text="ok"):
        self.status_code = status_code
        self.headers = headers or {}
        self.content = content
        self.text = text


def test_gestao_gera_relatorio_e_reavalia_vulnerabilidades(tmp_path):
    anterior = Vulnerabilidade(
        identificador="A02-OLD",
        categoria="A02",
        titulo="Exemplo antigo",
        descricao="Exemplo",
        ativo="https://example.com",
        severidade="MEDIA",
    )
    atual = Vulnerabilidade(
        identificador="A02-NEW",
        categoria="A02",
        titulo="Exemplo novo",
        descricao="Exemplo",
        ativo="https://example.com",
        severidade="ALTA",
    )

    consolidados = reavaliar([anterior], [atual])
    assert len(consolidados) == 2
    assert any(v.corrigida for v in consolidados)

    relatorio = gerar_relatorio(priorizar(consolidados), "https://example.com")
    assert relatorio["json"].endswith(".json")
    assert os.path.exists(relatorio["json"])
    assert os.path.exists(relatorio["txt"])
    assert os.path.exists(Path(relatorio["frontend"]))


def test_coleta_resolve_host_e_headers(monkeypatch):
    def fake_getaddrinfo(host, port):
        return [(None, None, None, None, ("8.8.8.8", 443))]

    class FakeResponseHTTP(FakeResponse):
        pass

    response = FakeResponseHTTP(status_code=200, headers={"Server": "nginx/1.23"})

    monkeypatch.setattr("modulos.coleta.socket.getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr("modulos.coleta.requests.get", lambda *args, **kwargs: response)

    info = coletar_informacoes("https://example.com")
    assert info["host"] == "example.com"
    assert info["enderecos_ip"] == ["8.8.8.8"]
    assert info["status_http"] == 200
    assert info["servidor"] == "nginx/1.23"


def test_escanear_usa_nmap_quando_disponivel(monkeypatch):
    class FakeHostData(dict):
        def all_protocols(self):
            return ["tcp"]

    class FakeScanner:
        def __init__(self):
            self.called = False

        def scan(self, host, arguments):
            self.called = True
            self.host = host
            self.arguments = arguments

        def all_hosts(self):
            return ["127.0.0.1"]

        def __getitem__(self, host):
            return FakeHostData({"tcp": {21: {"state": "open", "name": "ftp", "product": "", "version": ""}}})

    scanner = FakeScanner()
    fake_nmap_module = types.SimpleNamespace(PortScanner=lambda: scanner)
    monkeypatch.setitem(sys.modules, "nmap", fake_nmap_module)
    monkeypatch.setattr("modulos.escaneamento.logger", types.SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None))
    monkeypatch.setattr("modulos.escaneamento._scan_socket", lambda host, portas: [])

    achados = escanear("127.0.0.1")
    assert scanner.called is True
    assert any("PORTA-21" in v.identificador for v in achados)


def test_escaneamento_fallback_socket(monkeypatch):
    class FakeSocket:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def settimeout(self, value):
            self.value = value

        def connect_ex(self, addr):
            return 0 if addr[1] == 21 else 1

    monkeypatch.setattr("modulos.escaneamento.socket.socket", FakeSocket)
    abertas = _scan_socket("127.0.0.1", [21, 22])
    assert abertas[0]["porta"] == 21


def test_analise_codigo_encontra_padroes_inseguros(tmp_path):
    subdir = tmp_path / "src"
    subdir.mkdir()
    arquivo = subdir / "app.py"
    arquivo.write_text(
        "SECRET = 'abc1234567890'\n"
        "eval(user_input)\n"
        "subprocess.run('ls', shell=True)\n",
        encoding="utf-8",
    )

    achados = analisar_diretorio(str(tmp_path))
    assert any(v.categoria == "A02" for v in achados)
    assert any(v.categoria == "A03" for v in achados)


def test_pentest_web_detecta_cabecalhos_e_caminhos(monkeypatch):
    responses = {}

    def fake_get(url, *args, **kwargs):
        if url.endswith("/admin"):
            return FakeResponse(status_code=200, headers={}, content=b"admin")
        if url.endswith("/admin/login"):
            return FakeResponse(status_code=200, headers={}, content=b"login")
        return FakeResponse(status_code=200, headers={"Server": "nginx/1.2"}, content=b"ok")

    monkeypatch.setattr("modulos.pentest.requests.get", fake_get)
    achados = pentest_web("https://example.com")
    assert any(v.identificador.startswith("A02-HDR") for v in achados)
    assert any(v.identificador.startswith("A01-PATH") for v in achados)


def test_sca_retornara_vulnerabilidades_quando_pip_audit_funciona(monkeypatch, tmp_path):
    requirements = tmp_path / "requirements.txt"
    requirements.write_text("requests>=2.31.0\n", encoding="utf-8")

    resultado = types.SimpleNamespace(
        returncode=0,
        stdout=json.dumps({
            "dependencies": [
                {"name": "requests", "version": "2.31.0", "vulns": [{"id": "PYSEC-123", "description": "CVE", "fix_versions": ["2.32.0"]}]}
            ]
        }),
    )
    monkeypatch.setattr("modulos.sca.subprocess.run", lambda *args, **kwargs: resultado)
    achados = analisar_dependencias(str(tmp_path))
    assert any(v.identificador == "A06-SCA-PYSEC-123" for v in achados)


def test_main_executa_um_ciclo_completo(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--alvo", "https://example.com", "--continuo", "0"])
    monkeypatch.setattr(main_module, "executar_ciclo", lambda alvo, codigo: [Vulnerabilidade(identificador="A01-TEST", categoria="A01", titulo="teste", descricao="teste", ativo=alvo, severidade="ALTA")])
    monkeypatch.setattr(main_module, "reavaliar", lambda anteriores, atuais: atuais)
    monkeypatch.setattr(main_module, "priorizar", lambda vulns: vulns)
    monkeypatch.setattr(main_module, "gerar_relatorio", lambda vulns, alvo: {"json": "x.json", "txt": "x.txt", "frontend": "x.json"})
    main_module.main()
