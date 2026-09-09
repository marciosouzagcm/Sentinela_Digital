import json
import tempfile
from pathlib import Path

from pdf_generator import gerar_pdf

payload = {
    "email": "usuario@provedor.com",
    "gerado_em": "2026-09-09T12:00:00Z",
    "ferramentas": {
        "h8mail": {
            "status": "success",
            "output_file": "",
            "data": {"lines": ["\u001b[31m[!] Banner\u001b[0m", "[+] usuario@provedor.com"]},
        },
        "sherlock": {
            "status": "success",
            "output_file": "",
            "data": {"lines": ["\u001b[32mNo result found\u001b[0m", "user@example.com"]},
        },
        "holehe": {
            "status": "success",
            "output_file": "",
            "data": {"lines": ["\u001b[33m[+] conta ativa\u001b[0m", "[+] github.com"]},
        },
        "ghunt": {
            "status": "auth_required",
            "output_file": "",
            "data": {"lines": ["\u001b[31mAuth failed: cookies expired\u001b[0m"]},
        },
    },
}

tmpdir = Path(tempfile.mkdtemp())
json_path = tmpdir / "relatorio_mestre.json"
pdf_path = tmpdir / "relatorio.pdf"
json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
resultado = gerar_pdf(json_path, pdf_path)
print("RESULT", resultado)
print("EXISTS", pdf_path.exists(), "SIZE", pdf_path.stat().st_size if pdf_path.exists() else 0)
