"""Adaptador independente para o recon-ng."""
from pathlib import Path
import subprocess
from typing import Any


def run_recon_ng(email: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "recon_ng.txt"
    resource_file = output_dir / "recon_ng_commands.rc"
    resource_file.write_text(
        f"search contacts {email}\nexit\n",
        encoding="utf-8",
    )
    command = ["recon-ng", "-r", str(resource_file)]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        raw_output = result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else "")
        status = "success" if result.returncode == 0 else "error"
        data = {"returncode": result.returncode, "resource_file": str(resource_file), "lines": [line.strip() for line in result.stdout.splitlines() if line.strip()]}
    except FileNotFoundError as exc:
        raw_output, status, data = f"Ferramenta não encontrada no PATH: {exc}", "unavailable", {"error": str(exc), "resource_file": str(resource_file)}
    except subprocess.TimeoutExpired as exc:
        raw_output, status, data = f"Execução excedeu o timeout de 120 segundos: {exc}", "timeout", {"error": str(exc), "resource_file": str(resource_file)}
    except OSError as exc:
        raw_output, status, data = f"Falha ao iniciar ferramenta: {exc}", "error", {"error": str(exc), "resource_file": str(resource_file)}
    output_file.write_text(raw_output, encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
