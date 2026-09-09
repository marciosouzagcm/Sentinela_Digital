"""Adaptador independente para o recon-ng."""
import re
import subprocess
from pathlib import Path
from typing import Any

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _limpar_saida(raw_output: str) -> str:
    return ANSI_ESCAPE_RE.sub("", raw_output or "").strip()


def run_recon_ng(email: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "recon_ng.txt"
    resource_file = output_dir / "recon_ng_commands.rc"
    resource_file.write_text(
        "\n".join(
            [
                "workspace add sentinela",
                "workspaces load sentinela",
                "modules load recon/contacts-contacts",
                "modules load profiler/templates",
                f"options set SOURCE {email}",
                "run",
                "exit",
                "",
            ]
        ),
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
        raw_output = _limpar_saida(result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else ""))
        status = "success" if result.returncode == 0 else "error"
        data = {
            "returncode": result.returncode,
            "resource_file": str(resource_file),
            "lines": [line.strip() for line in raw_output.splitlines() if line.strip()],
        }
    except FileNotFoundError as exc:
        raw_output, status, data = f"Ferramenta não encontrada no PATH: {exc}", "unavailable", {"error": str(exc), "resource_file": str(resource_file)}
    except subprocess.TimeoutExpired as exc:
        raw_output, status, data = f"Execução excedeu o timeout de 120 segundos: {exc}", "timeout", {"error": str(exc), "resource_file": str(resource_file)}
    except OSError as exc:
        raw_output, status, data = f"Falha ao iniciar ferramenta: {exc}", "error", {"error": str(exc), "resource_file": str(resource_file)}
    output_file.write_text(_limpar_saida(raw_output), encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
