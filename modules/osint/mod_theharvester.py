"""Adaptador independente para o theHarvester."""
from pathlib import Path
import subprocess
from typing import Any, Optional


def _extrair_dominio(valor: str) -> Optional[str]:
    """Extrai e valida o domínio de um e-mail ou domínio recebido."""
    entrada = valor.strip()
    if "@" in entrada:
        partes = entrada.rsplit("@", 1)
        if len(partes) != 2 or not partes[0] or not partes[1]:
            return None
        dominio = partes[1]
    else:
        dominio = entrada

    dominio = dominio.strip().lower().rstrip(".")
    if not dominio or "." not in dominio or any(char.isspace() for char in dominio):
        return None
    if any(char in dominio for char in "/\\:@"):
        return None
    return dominio


def run_theharvester(email: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "theharvester.txt"
    domain = _extrair_dominio(email)
    if domain is None:
        raw_output = f"Entrada inválida: não foi possível extrair um domínio de {email!r}."
        output_file.write_text(raw_output, encoding="utf-8")
        return {
            "status": "invalid_input",
            "output_file": str(output_file),
            "data": {"error": raw_output},
        }

    try:
        result = subprocess.run(
            ["theHarvester", "-d", domain, "-b", "google,bing,duckduckgo,crtsh"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
        raw_output = result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else "")
        status = "success" if result.returncode == 0 else "error"
        data = {"returncode": result.returncode, "domain": domain, "lines": [line.strip() for line in result.stdout.splitlines() if line.strip()]}
    except FileNotFoundError as exc:
        raw_output, status, data = f"Ferramenta não encontrada no PATH: {exc}", "unavailable", {"error": str(exc), "domain": domain}
    except subprocess.TimeoutExpired as exc:
        raw_output, status, data = f"Execução excedeu o timeout de 120 segundos: {exc}", "timeout", {"error": str(exc), "domain": domain}
    except OSError as exc:
        raw_output, status, data = f"Falha ao iniciar ferramenta: {exc}", "error", {"error": str(exc), "domain": domain}
    output_file.write_text(raw_output, encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
