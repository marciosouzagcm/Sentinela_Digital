"""Adaptador independente para o Holehe."""
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _limpar_saida(raw_output: str) -> str:
    return ANSI_ESCAPE_RE.sub("", raw_output or "").strip()


def _obter_timeout() -> int:
    try:
        return max(10, int(os.getenv("OSINT_TIMEOUT_SECONDS", "120")))
    except ValueError:
        return 120


def _obter_delay() -> float:
    try:
        return max(0.0, float(os.getenv("OSINT_RATE_LIMIT_DELAY", "0.25")))
    except ValueError:
        return 0.25


def run_holehe(email: str, output_dir: Path) -> dict[str, Any]:
    """Executa o Holehe para um e-mail autorizado e salva a saída bruta."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "holehe.txt"
    command = ["holehe", email]
    delay = _obter_delay()
    timeout = _obter_timeout()
    if delay > 0:
        time.sleep(delay)
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False)
        raw_output = _limpar_saida(result.stdout + ("\n[stderr]\n" + result.stderr if result.stderr else ""))
        status = "success" if result.returncode == 0 else "error"
        lowered = raw_output.lower()
        if "rate limit" in lowered or "[x]" in raw_output:
            status = "rate_limited"
        data = {"returncode": result.returncode, "timeout_seconds": timeout, "rate_limit_delay": delay, "lines": [line.strip() for line in raw_output.splitlines() if line.strip()]}
    except FileNotFoundError as exc:
        raw_output = f"Ferramenta não encontrada no PATH: {exc}"
        status, data = "unavailable", {"error": str(exc), "timeout_seconds": timeout, "rate_limit_delay": delay}
    except subprocess.TimeoutExpired as exc:
        raw_output = f"Execução excedeu o timeout de {timeout} segundos: {exc}"
        status, data = "timeout", {"error": str(exc), "timeout_seconds": timeout, "rate_limit_delay": delay}
    except OSError as exc:
        raw_output = f"Falha ao iniciar ferramenta: {exc}"
        status, data = "error", {"error": str(exc), "timeout_seconds": timeout, "rate_limit_delay": delay}
    output_file.write_text(raw_output, encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
