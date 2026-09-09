"""Adaptador independente para o theHarvester."""
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Optional

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


def _limpar_saida(raw_output: str) -> str:
    return ANSI_ESCAPE_RE.sub("", raw_output or "").strip()


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


def _carregar_config_api() -> dict[str, str]:
    config: dict[str, str] = {}
    for nome in ("HUNTER_API_KEY", "SHODAN_API_KEY"):
        valor = os.getenv(nome)
        if valor:
            config[nome] = valor

    for caminho_base in (Path.cwd(), Path(__file__).resolve().parents[2]):
        for nome in (".env", "config.json"):
            arquivo = caminho_base / nome
            if not arquivo.exists():
                continue
            if arquivo.suffix == ".json":
                try:
                    with arquivo.open("r", encoding="utf-8") as handle:
                        dados = json.load(handle)
                    if isinstance(dados, dict):
                        for chave in ("HUNTER_API_KEY", "SHODAN_API_KEY"):
                            valor = dados.get(chave)
                            if valor:
                                config[chave] = str(valor)
                except (json.JSONDecodeError, OSError):
                    continue
            elif arquivo.name == ".env":
                try:
                    for linha in arquivo.read_text(encoding="utf-8").splitlines():
                        if "=" not in linha or linha.strip().startswith("#"):
                            continue
                        chave, valor = linha.split("=", 1)
                        chave = chave.strip()
                        valor = valor.strip().strip('"\'')
                        if chave in {"HUNTER_API_KEY", "SHODAN_API_KEY"} and valor:
                            config[chave] = valor
                except OSError:
                    continue
    return config


def run_theharvester(email: str, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "theharvester.txt"
    domain = _extrair_dominio(email)
    if domain is None:
        raw_output = f"Entrada inválida: não foi possível extrair um domínio de {email!r}."
        output_file.write_text(_limpar_saida(raw_output), encoding="utf-8")
        return {
            "status": "invalid_input",
            "output_file": str(output_file),
            "data": {"error": raw_output},
        }

    api_config = _carregar_config_api()
    env = os.environ.copy()
    env.update({key: value for key, value in api_config.items() if value})
    try:
        result = subprocess.run(
            ["theHarvester", "-d", domain, "-b", "duckduckgo,crtsh,securitytrails"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
            env=env,
        )
        raw_output = _limpar_saida(result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else ""))
        status = "success" if result.returncode == 0 else "error"
        if any(token in raw_output.lower() for token in ("deprecated", "google", "bing")):
            status = "warning"
        data = {
            "returncode": result.returncode,
            "domain": domain,
            "api_keys": {key: "configured" for key in sorted(api_config)},
            "lines": [line.strip() for line in raw_output.splitlines() if line.strip()],
        }
    except FileNotFoundError as exc:
        raw_output, status, data = f"Ferramenta não encontrada no PATH: {exc}", "unavailable", {"error": str(exc), "domain": domain, "api_keys": {key: "configured" for key in sorted(api_config)}}
    except subprocess.TimeoutExpired as exc:
        raw_output, status, data = f"Execução excedeu o timeout de 120 segundos: {exc}", "timeout", {"error": str(exc), "domain": domain, "api_keys": {key: "configured" for key in sorted(api_config)}}
    except OSError as exc:
        raw_output, status, data = f"Falha ao iniciar ferramenta: {exc}", "error", {"error": str(exc), "domain": domain, "api_keys": {key: "configured" for key in sorted(api_config)}}
    output_file.write_text(raw_output, encoding="utf-8")
    return {"status": status, "output_file": str(output_file), "data": data}
