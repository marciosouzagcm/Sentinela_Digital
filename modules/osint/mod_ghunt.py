"""Adaptador independente para o GHunt."""
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _limpar_saida(raw_output: str) -> str:
    return ANSI_ESCAPE_RE.sub("", raw_output or "").strip()


def _resolver_cookies_ghunt() -> str | None:
    caminhos = []
    valor = os.getenv("GHUNT_COOKIES_FILE")
    if valor:
        caminhos.append(Path(valor))
    caminhos.extend(
        [
            Path.cwd() / "cookies.json",
            Path.home() / ".config" / "ghunt" / "cookies.json",
            Path.home() / ".ghunt" / "cookies.json",
        ]
    )
    for caminho in caminhos:
        if caminho.exists():
            return str(caminho)
    return None


def run_ghunt(email: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "ghunt.txt"
    cookies_file = _resolver_cookies_ghunt()
    if not cookies_file:
        raw_output = (
            "GHunt não pode ser executado porque o arquivo de cookies do Google não foi encontrado. "
            "Configure GHUNT_COOKIES_FILE ou deixe um arquivo cookies.json no diretório do projeto."
        )
        logger.warning(raw_output)
        mensagem = _limpar_saida(raw_output)
        output_file.write_text(mensagem, encoding="utf-8")
        return {
            "status": "skipped",
            "output_file": str(output_file),
            "data": {"warning": mensagem, "cookies_file": None},
        }

    env = os.environ.copy()
    env["GHUNT_COOKIES_FILE"] = cookies_file
    try:
        result = subprocess.run(
            ["ghunt", "email", email],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
            env=env,
        )
        raw_output = _limpar_saida(result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else ""))
        output_text = raw_output or "GHunt finalizou sem mensagem de saída."
        status = "success" if result.returncode == 0 else "error"
        lowered = output_text.lower()
        if result.returncode != 0 and any(token in lowered for token in ("auth", "cookie", "expired", "login", "google")):
            status = "skipped"
        data = {
            "returncode": result.returncode,
            "cookies_file": cookies_file,
            "warning": "Cookies ausentes ou expirados; execução interrompida." if status == "skipped" else None,
            "lines": [line.strip() for line in output_text.splitlines() if line.strip()],
        }
    except FileNotFoundError as exc:
        raw_output, status, data = (
            f"Ferramenta não encontrada no PATH: {exc}",
            "unavailable",
            {"error": str(exc), "cookies_file": cookies_file},
        )
    except subprocess.TimeoutExpired as exc:
        raw_output, status, data = (
            f"Execução excedeu o timeout de 180 segundos: {exc}",
            "timeout",
            {"error": str(exc), "cookies_file": cookies_file},
        )
    except OSError as exc:
        raw_output, status, data = (
            f"Falha ao iniciar ferramenta: {exc}",
            "error",
            {"error": str(exc), "cookies_file": cookies_file},
        )
    output_file.write_text(_limpar_saida(raw_output), encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
