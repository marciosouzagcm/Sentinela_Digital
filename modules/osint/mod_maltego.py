"""Adaptador independente para o Maltego."""
from pathlib import Path
import subprocess
from typing import Any


def run_maltego(email: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "maltego.txt"
    command = ["maltego", "--transform", "email", email]
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
        if result.returncode == 0:
            status = "success"
            data = {"returncode": result.returncode, "lines": [line.strip() for line in result.stdout.splitlines() if line.strip()]}
        else:
            status = "skipped"
            message = (
                "Maltego não executou como CLI puro; a ferramenta pode exigir "
                "interface gráfica e licenciamento/autenticação prévia."
            )
            raw_output = f"{message}\n{raw_output}".rstrip() + "\n"
            data = {
                "returncode": result.returncode,
                "reason": message,
                "lines": [line.strip() for line in result.stdout.splitlines() if line.strip()],
            }
    except FileNotFoundError as exc:
        raw_output, status, data = f"Ferramenta não encontrada no PATH: {exc}", "unavailable", {"error": str(exc)}
    except subprocess.TimeoutExpired as exc:
        raw_output = (
            "Maltego requer interface gráfica/licenciamento prévio e excedeu o "
            f"timeout de 180 segundos: {exc}"
        )
        status, data = "skipped", {"error": str(exc), "reason": raw_output}
    except OSError as exc:
        raw_output = f"Maltego não pôde ser iniciado em modo CLI: {exc}"
        status, data = "skipped", {"error": str(exc), "reason": raw_output}
    output_file.write_text(raw_output, encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
