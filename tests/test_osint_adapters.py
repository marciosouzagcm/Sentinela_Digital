import types
from pathlib import Path

from modules.osint.mod_ghunt import run_ghunt
from modules.osint.mod_holehe import run_holehe
from modules.osint.mod_recon_ng import run_recon_ng
from modules.osint.mod_theharvester import run_theharvester


def test_run_ghunt_requires_valid_cookies_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))

    resultado = run_ghunt("user@example.com", tmp_path)

    assert resultado["status"] == "skipped"
    assert "cookies.json" in resultado["data"]["warning"].lower()


def test_run_ghunt_skips_when_cookies_are_expired(tmp_path, monkeypatch):
    (tmp_path / "cookies.json").write_text("{}", encoding="utf-8")

    def fake_run(command, **kwargs):
        return types.SimpleNamespace(returncode=1, stdout="cookies expired", stderr="")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("modules.osint.mod_ghunt.subprocess.run", fake_run)

    resultado = run_ghunt("user@example.com", tmp_path)

    assert resultado["status"] == "skipped"
    assert resultado["data"]["warning"]


def test_run_recon_ng_uses_valid_recon_commands(tmp_path, monkeypatch):
    resource_path = tmp_path / "recon_ng_commands.rc"

    def fake_run(command, **kwargs):
        resource_path.write_text(Path(command[2]).read_text(encoding="utf-8"), encoding="utf-8")
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("modules.osint.mod_recon_ng.subprocess.run", fake_run)

    run_recon_ng("user@example.com", tmp_path)

    script = resource_path.read_text(encoding="utf-8")
    assert "search contacts" not in script
    assert "modules load recon/contacts-contacts" in script
    assert "options set SOURCE user@example.com" in script


def test_run_theharvester_ignores_deprecated_sources_and_uses_configured_keys(monkeypatch, tmp_path):
    captured = {}

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs.get("env", {})
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setenv("HUNTER_API_KEY", "hunter-secret")
    monkeypatch.setenv("SHODAN_API_KEY", "shodan-secret")
    monkeypatch.setattr("modules.osint.mod_theharvester.subprocess.run", fake_run)

    run_theharvester("user@example.com", tmp_path)

    comando = " ".join(captured["command"])
    assert "google" not in comando.lower()
    assert "bing" not in comando.lower()
    assert captured["env"].get("HUNTER_API_KEY") == "hunter-secret"
    assert captured["env"].get("SHODAN_API_KEY") == "shodan-secret"


def test_run_holehe_uses_timeout_and_rate_limit_delay(monkeypatch, tmp_path):
    calls = []

    def fake_sleep(seconds):
        calls.append(("sleep", seconds))

    def fake_run(command, **kwargs):
        calls.append(("timeout", kwargs.get("timeout")))
        return types.SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setenv("OSINT_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("OSINT_RATE_LIMIT_DELAY", "0.25")
    monkeypatch.setattr("modules.osint.mod_holehe.time.sleep", fake_sleep)
    monkeypatch.setattr("modules.osint.mod_holehe.subprocess.run", fake_run)

    run_holehe("user@example.com", tmp_path)

    assert any(item == ("timeout", 45) for item in calls)
    assert any(item[0] == "sleep" for item in calls)
