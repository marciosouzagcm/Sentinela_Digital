from __future__ import annotations

import json
from pathlib import Path

root = Path(__file__).resolve().parent
output_path = root / "reports" / "relatorio_mestre_sintetico.json"
output_path.parent.mkdir(parents=True, exist_ok=True)

payload = {
    "email": "usuario@provedor.com",
    "gerado_em": "2026-09-09T12:00:00Z",
    "ferramentas": {
        "holehe": {
            "status": "success",
            "output_file": str(output_path.parent / "holehe_sintetico.txt"),
            "data": {
                "lines": [
                    "[+] Conta ativa encontrada para usuario@provedor.com",
                    "[+] github.com",
                    "[+] linkedin.com",
                    "[+] twitch.tv",
                ]
            },
            "destaques": [
                "[+] Conta ativa encontrada para usuario@provedor.com",
                "[+] github.com",
                "[+] linkedin.com",
                "[+] twitch.tv",
            ],
            "resumo": "Contas ativas confirmadas."
        },
        "h8mail": {
            "status": "success",
            "output_file": str(output_path.parent / "h8mail_sintetico.txt"),
            "data": {
                "lines": [
                    "[found] breach for usuario@provedor.com",
                    "password: senha123@2026",
                    "leak source: pastebin",
                    "email: usuario@provedor.com",
                ]
            },
            "destaques": [
                "[found] breach for usuario@provedor.com",
                "password: senha123@2026",
                "leak source: pastebin",
            ],
            "resumo": "Execução concluída com resultados relevantes."
        },
        "gitleaks": {
            "status": "success",
            "output_file": str(output_path.parent / "gitleaks_sintetico.txt"),
            "data": {
                "lines": [
                    "No leaks found",
                    "0 findings",
                    "Repository scan completed without sensitive content.",
                ]
            },
            "destaques": [
                "No leaks found",
                "0 findings",
            ],
            "resumo": "Varredura concluída. Nenhum vazamento detectado."
        },
        "sherlock": {
            "status": "success",
            "output_file": str(output_path.parent / "sherlock_sintetico.txt"),
            "data": {
                "lines": [
                    "No result found",
                    "Sem resultados relevantes",
                ]
            },
            "destaques": [
                "No result found",
            ],
            "resumo": "Execução concluída sem evidência útil."
        },
        "ghunt": {
            "status": "skipped",
            "output_file": str(output_path.parent / "ghunt_sintetico.txt"),
            "data": {
                "warning": "GHunt não pode ser executado porque o arquivo de cookies do Google não foi encontrado.",
                "lines": [
                    "GHunt não pode ser executado porque o arquivo de cookies do Google não foi encontrado.",
                ]
            },
            "destaques": [],
            "resumo": "Execução ignorada ou configuração pendente."
        }
    }
}

output_path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
print(output_path)
