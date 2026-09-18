from pathlib import Path

from main import _executar_ferramenta, executar_pipeline_web, redact_sensitive
from modulos.utilidades import Vulnerabilidade
from pdf_generator import _calcular_score_exposicao, parse_ghunt, parse_holehe


def test_redact_sensitive_masks_credentials_and_calendar_urls():
    payload = {
        "lines": [
            "password: senha123",
            "Gaia ID: 123456789012345",
            "https://calendar.google.com/calendar/ical/user@example.com/public/basic.ics",
        ]
    }

    sanitized = redact_sensitive(payload)

    assert "senha123" not in str(sanitized)
    assert "123456789012345" not in str(sanitized)
    assert "calendar.google.com/calendar/ical/" not in str(sanitized)


def test_holehe_parser_separates_confirmed_rate_limited_and_negative():
    parsed = parse_holehe({"data": {"lines": [
        "[+] github.com",
        "[x] twitter.com",
        "[-] example.com",
    ]}})

    assert parsed == {
        "confirmed": ["github.com"],
        "rate_limited": ["twitter.com"],
        "negative": ["example.com"],
    }


def test_failed_tools_do_not_raise_exposure_score():
    report = {
        "ferramentas": {
            "h8mail": {"status": "error", "data": {"lines": ["breach found"]}},
            "holehe": {"status": "unavailable", "data": {"lines": ["[+] github.com"]}},
        }
    }

    assert _calcular_score_exposicao(report) == 0


def test_ghunt_parser_extracts_public_calendar_and_events():
    parsed = parse_ghunt({"data": {"lines": [
        "[+] Authenticated !",
        "[+] Public Google Calendar found !",
        "[+] 68 events dumped !",
    ]}})

    assert parsed["authenticated"] is True
    assert parsed["calendar_public"] is True
    assert parsed["event_count"] == 68


def test_precheck_marks_missing_binary_without_calling_adapter(tmp_path, monkeypatch):
    called = False

    def adapter(email: str, output_dir: Path):
        nonlocal called
        called = True
        return {"status": "success", "data": {}}

    monkeypatch.setattr("main.shutil.which", lambda _: None)
    name, result = _executar_ferramenta("gitleaks", adapter, "user@example.com", tmp_path)

    assert name == "gitleaks"
    assert result["status"] == "unavailable"
    assert called is False
    assert result["data"]["duration_ms"] >= 0


def test_web_pipeline_writes_master_json_and_pdf_to_reports(tmp_path, monkeypatch):
    monkeypatch.setattr("main.coletar_informacoes", lambda alvo: {"alvo_original": alvo, "host": "example.com"})
    monkeypatch.setattr("main.escanear", lambda host: [Vulnerabilidade(
        identificador="A05-TEST", categoria="A05", titulo="Header ausente",
        descricao="Header de segurança ausente.", ativo="https://example.com",
        severidade="MEDIA", evidencia="Headers: []", mitigacao="Adicionar o header.",
    )])
    monkeypatch.setattr("main.pentest_web", lambda alvo: [])

    resultado = executar_pipeline_web("https://example.com", base_dir=tmp_path)

    mestre = Path(resultado["relatorio_mestre"])
    pdf = Path(resultado["pdf"])
    assert mestre.parent == tmp_path
    assert mestre.name.startswith("relatorio_mestre_example.com_")
    assert mestre.suffix == ".json"
    assert pdf.name.removesuffix(".pdf") == mestre.name.removesuffix(".json")
    assert mestre.exists()
    assert pdf.exists()
    assert pdf.stat().st_size > 0