"""Adaptador independente para o GHunt."""
from pathlib import Path
import subprocess
from typing import Any


def run_ghunt(email: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "ghunt.txt"
    try:
        result = subprocess.run(["ghunt", "email", email], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False)
        raw_output = result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else "")
        status = "success" if result.returncode == 0 else "error"
        data = {"returncode": result.returncode, "lines": [line.strip() for line in result.stdout.splitlines() if line.strip()]}
    except FileNotFoundError as exc:
        raw_output, status, data = f"Ferramenta não encontrada no PATH: {exc}", "unavailable", {"error": str(exc)}
    except subprocess.TimeoutExpired as exc:
        raw_output, status, data = f"Execução excedeu o timeout de 180 segundos: {exc}", "timeout", {"error": str(exc)}
    except OSError as exc:
        raw_output, status, data = f"Falha ao iniciar ferramenta: {exc}", "error", {"error": str(exc)}
    output_file.write_text(raw_output, encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
