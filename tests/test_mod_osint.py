import types

import pytest

from modules.osint.mod_h8mail import run_h8mail
from modules.osint.mod_holehe import run_holehe
from modules.osint.mod_maltego import run_maltego
from modules.osint.mod_recon_ng import run_recon_ng


def completed(stdout="ok", stderr="", returncode=0):
    return types.SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_h8mail_warns_without_paid_api_key(tmp_path, monkeypatch):
    monkeypatch.delenv("HUNTER_API_KEY", raising=False)
    result = run_h8mail("user@example.com", tmp_path)
    assert result["status"] == "warning"
    assert "HUNTER_API_KEY" in result["data"]["warning"]


def test_h8mail_warns_when_scylla_is_down(tmp_path, monkeypatch):
    monkeypatch.setenv("HUNTER_API_KEY", "configured")
    monkeypatch.setattr("modules.osint.mod_h8mail.shutil.which", lambda _: "h8mail")
    monkeypatch.setattr(
        "modules.osint.mod_h8mail.subprocess.run",
        lambda *args, **kwargs: completed("scylla.so connection timeout", returncode=1),
    )
    result = run_h8mail("user@example.com", tmp_path)
    assert result["status"] == "warning"
    assert "scylla.so" in result["data"]["warning"]


def test_h8mail_handles_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("HUNTER_API_KEY", "configured")
    monkeypatch.setattr("modules.osint.mod_h8mail.shutil.which", lambda _: "h8mail")
    monkeypatch.setattr(
        "modules.osint.mod_h8mail.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(__import__("subprocess").TimeoutExpired("h8mail", 120)),
    )
    result = run_h8mail("user@example.com", tmp_path)
    assert result["status"] == "timeout"


def test_recon_ng_uses_v5_workspace_command_and_rejects_cli_error(tmp_path, monkeypatch):
    captured = {}

    def fake_run(command, **kwargs):
        captured["resource"] = open(command[2], encoding="utf-8").read()
        return completed("Invalid command: workspace add", returncode=0)

    monkeypatch.setattr("modules.osint.mod_recon_ng.subprocess.run", fake_run)
    result = run_recon_ng("user@example.com", tmp_path)
    assert "workspaces create sentinela" in captured["resource"]
    assert "workspace add sentinela" not in captured["resource"]
    assert result["status"] == "error"


def test_holehe_separates_result_categories(tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_RATE_LIMIT_DELAY", "0")
    monkeypatch.setattr(
        "modules.osint.mod_holehe.subprocess.run",
        lambda *args, **kwargs: completed("[+] github.com\n[x] twitter.com\n[-] example.com"),
    )
    result = run_holehe("user@example.com", tmp_path)
    assert result["data"]["contas_confirmadas"] == ["github.com"]
    assert result["data"]["contas_limite_taxa"] == ["twitter.com"]
    assert result["data"]["nao_registrado"] == ["example.com"]
    assert result["status"] == "rate_limited"


def test_holehe_handles_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("OSINT_RATE_LIMIT_DELAY", "0")
    monkeypatch.setattr(
        "modules.osint.mod_holehe.subprocess.run",
        lambda *args, **kwargs: (_ for _ in ()).throw(__import__("subprocess").TimeoutExpired("holehe", 120)),
    )
    result = run_holehe("user@example.com", tmp_path)
    assert result["status"] == "timeout"


def test_maltego_skips_headless_without_running_process(tmp_path, monkeypatch):
    monkeypatch.setattr("modules.osint.mod_maltego.os.name", "posix")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.setattr("modules.osint.mod_maltego.subprocess.run", pytest.fail)
    result = run_maltego("user@example.com", tmp_path)
    assert result["status"] == "skipped"
    assert result["data"]["headless"] is True
