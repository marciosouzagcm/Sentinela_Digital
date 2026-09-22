"""Adaptador independente para o h8mail."""
from pathlib import Path
import os
import shutil
import subprocess
from typing import Any


def run_h8mail(email: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "h8mail.txt"
    hunter_key = os.getenv("HUNTER_API_KEY", "").strip()
    if not hunter_key:
        message = (
            "HUNTER_API_KEY não configurada; fontes pagas do h8mail foram "
            "ignoradas. A execução pública pode continuar sem essa fonte."
        )
        output_file.write_text(message, encoding="utf-8")
        return {
            "status": "warning",
            "output_file": str(output_file),
            "data": {"warning": message, "lines": [message], "sources_skipped": ["hunter.io"]},
        }
    if shutil.which("h8mail") is None:
        message = "Executável h8mail não encontrado no PATH; consulta não realizada."
        output_file.write_text(message, encoding="utf-8")
        return {
            "status": "unavailable",
            "output_file": str(output_file),
            "data": {"error": message, "lines": [message]},
        }
    try:
        result = subprocess.run(
            ["h8mail", "-t", email],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        raw_output = result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else "")
        lowered = raw_output.lower()
        source_down = "scylla.so" in lowered and any(
            marker in lowered for marker in ("down", "unavailable", "timeout", "connection")
        )
        status = "warning" if source_down else ("success" if result.returncode == 0 else "error")
        warning = (
            "A fonte scylla.so está indisponível no momento; o resultado pode estar incompleto."
            if source_down
            else None
        )
        if warning:
            raw_output = f"{warning}\n{raw_output}".strip()
        data = {"returncode": result.returncode, "lines": [line.strip() for line in result.stdout.splitlines() if line.strip()]}
        if warning:
            data["warning"] = warning
    except FileNotFoundError as exc:
        raw_output, status, data = f"Ferramenta não encontrada no PATH: {exc}", "unavailable", {"error": str(exc)}
    except subprocess.TimeoutExpired as exc:
        raw_output, status, data = f"Execução excedeu o timeout de 120 segundos: {exc}", "timeout", {"error": str(exc)}
    except OSError as exc:
        raw_output, status, data = f"Falha ao iniciar ferramenta: {exc}", "error", {"error": str(exc)}
    output_file.write_text(raw_output, encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
