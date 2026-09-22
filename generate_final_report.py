from pathlib import Path
from pdf_generator import generate_pdf

src = Path("C:/Users/DELL/Sentinela_Digital/reports/relatorio_mestre (4).json")
out = Path("C:/Users/DELL/Sentinela_Digital/reports/relatorio_final_marciosouzagcm_gmail_com_20260914_134637.pdf")

if not src.exists():
    raise FileNotFoundError(f"Arquivo de origem não encontrado: {src}")

pdf_path = generate_pdf(str(src), str(out), "Equipe de Inteligência Cibernética")
print(f"PDF_FINAL={pdf_path}")
