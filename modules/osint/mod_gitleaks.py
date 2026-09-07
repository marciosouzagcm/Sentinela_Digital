"""Adaptador independente para o Gitleaks."""
from pathlib import Path
import subprocess
from typing import Any


def run_gitleaks(email: str, output_dir: Path) -> dict[str, Any]:
    """Executa o Gitleaks no diretório do scan e salva a saída bruta."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "gitleaks.txt"
    command = [
        "gitleaks",
        "dir",
        str(output_dir),
        "--no-banner",
        "--redact",
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )
        raw_output = result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else "")
        status = "success" if result.returncode in (0, 1) else "error"
        data = {
            "returncode": result.returncode,
            "email": email,
            "lines": [line.strip() for line in result.stdout.splitlines() if line.strip()],
        }
    except FileNotFoundError as exc:
        raw_output = f"Ferramenta não encontrada no PATH: {exc}"
        status, data = "unavailable", {"error": str(exc), "email": email}
    except subprocess.TimeoutExpired as exc:
        raw_output = f"Execução excedeu o timeout de 180 segundos: {exc}"
        status, data = "timeout", {"error": str(exc), "email": email}
    except OSError as exc:
        raw_output = f"Falha ao iniciar ferramenta: {exc}"
        status, data = "error", {"error": str(exc), "email": email}
    output_file.write_text(raw_output, encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
