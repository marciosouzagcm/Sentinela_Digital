from pathlib import Path

from main import _executar_ferramenta, redact_sensitive
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