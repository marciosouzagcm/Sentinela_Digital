import json
import re
import sys
from pathlib import Path
from typing import Any

from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
ASCII_BANNER_RE = re.compile(r"^(?:[\-=*_#/+|\\]{3,}|\s*[A-Z0-9_\-]{3,}\s*)$")


class NumberedCanvas(Canvas):
    def showPage(self):
        super().showPage()


def _sanitizar_texto(valor: Any) -> str:
    if valor is None:
        return ""
    texto = str(valor)
    texto = ANSI_ESCAPE_RE.sub("", texto)
    texto = texto.replace("\r", "\n")
    linhas = []
    for linha in texto.split("\n"):
        linha = linha.strip()
        if not linha:
            continue
        if ASCII_BANNER_RE.match(linha):
            continue
        if "\x00" in linha:
            continue
        linhas.append(linha)
    return "\n".join(linhas)


def _coletar_linhas(raw: Any) -> list[str]:
    if isinstance(raw, list):
        itens = raw
    elif isinstance(raw, str):
        itens = raw.splitlines()
    elif isinstance(raw, dict):
        itens = raw.get("lines", [])
    else:
        itens = []

    linhas: list[str] = []
    for item in itens:
        texto = _sanitizar_texto(item)
        if texto:
            linhas.append(texto)
    return linhas


def _normalizar_status(status: Any) -> str:
    if not status:
        return "unknown"
    return str(status).strip().lower()


def _extrair_destaques_holehe(linhas: list[str]) -> list[str]:
    destaques: list[str] = []
    for linha in linhas:
        if "[+]" in linha:
            destaque = linha.replace("[+]", "").strip()
            if destaque:
                destaques.append(destaque)
    if not destaques:
        for linha in linhas:
            if "rate limit" in linha.lower() or "error" in linha.lower() or "unavailable" in linha.lower():
                destaques.append(linha)
    return destaques[:6]


def _extrair_destaques_ghunt(linhas: list[str]) -> list[str]:
    destaques: list[str] = []
    for linha in linhas:
        if any(token in linha.lower() for token in ["found", "match", "account", "profile", "login", "google"]):
            destaques.append(linha)
    return destaques[:5]


def _extrair_destaques_sherlock(linhas: list[str]) -> list[str]:
    destaques: list[str] = []
    for linha in linhas:
        normal = linha.lower()
        if "[+]" in linha:
            continue
        if any(token in normal for token in ["found", "match", "profile", "account", "username", "service", "site"]):
            if "user@example.com" not in normal and "@" not in normal:
                destaques.append(linha)
    return destaques[:5]


def _resumo_ferramenta(nome: str, detalhe: Any) -> dict[str, Any]:
    status = _normalizar_status((detalhe or {}).get("status") if isinstance(detalhe, dict) else None)
    dados = (detalhe or {}).get("data", {}) if isinstance(detalhe, dict) else {}
    linhas = _coletar_linhas(dados.get("lines", []))
    if not linhas and isinstance(detalhe, dict) and detalhe.get("output_file"):
        try:
            with open(detalhe["output_file"], "r", encoding="utf-8") as handle:
                linhas = _coletar_linhas(handle.read())
        except OSError:
            linhas = []

    if nome == "sherlock":
        linhas = [linha for linha in linhas if not re.search(r"@\w+\.\w+", linha) and not re.search(r"\buser@example\.com\b", linha, re.I)]
        final_status = status
        if status == "success" and not _extrair_destaques_sherlock(linhas):
            final_status = "filtered"
        return {
            "status": final_status,
            "resumo": "Consulta de e-mail completo filtrada como falso positivo." if final_status == "filtered" else ("Sem resultados relevantes confirmados." if not linhas else "Resultados relevantes encontrados."),
            "destaques": _extrair_destaques_sherlock(linhas),
            "linhas": linhas[:10],
        }

    if nome == "holehe":
        destaques = _extrair_destaques_holehe(linhas)
        resumo = "Contas ativas confirmadas." if destaques else "Sem contas ativas confirmadas."
        return {
            "status": status,
            "resumo": resumo,
            "destaques": destaques,
            "linhas": linhas[:10],
        }

    if nome == "ghunt":
        destaques = _extrair_destaques_ghunt(linhas)
        resumo = "Achados relevantes do GHunt." if destaques else "GHunt sem achados confirmados."
        return {
            "status": status,
            "resumo": resumo,
            "destaques": destaques,
            "linhas": linhas[:10],
        }

    if nome in {"h8mail", "recon_ng", "theharvester", "emailharvester", "gitleaks", "maltego", "sherlock"}:
        status_text = status
        if status == "success" and not linhas:
            status_text = "no_data"
        resumo = "Execução concluída sem evidência útil." if status_text in {"success", "no_data"} and not linhas else "Execução concluída com resultados relevantes."
        return {
            "status": status_text,
            "resumo": resumo,
            "destaques": linhas[:5],
            "linhas": linhas[:10],
        }

    return {
        "status": status,
        "resumo": "Status da ferramenta registrado.",
        "destaques": linhas[:5],
        "linhas": linhas[:10],
    }


def _calcular_score_exposicao(resumo: dict[str, Any]) -> int:
    pesos = {
        "success": 12,
        "filtered": 28,
        "skipped": 35,
        "no_data": 42,
        "warning": 60,
        "auth_required": 75,
        "error": 88,
        "timeout": 82,
        "unavailable": 90,
        "unknown": 55,
    }
    if not resumo.get("ferramentas"):
        return 50

    total = 0
    for detalhe in resumo["ferramentas"].values():
        status = str(detalhe.get("status", "unknown")).strip().lower()
        total += pesos.get(status, 55)
    return max(0, min(100, int(round(total / len(resumo["ferramentas"])))))


def _resumo_executivo(dados: dict[str, Any]) -> dict[str, Any]:
    email = dados.get("email") or dados.get("alvo") or "N/A"
    gerado_em = dados.get("gerado_em", "N/A")
    ferramentas_raw = dados.get("ferramentas", {})
    ferramentas = {}
    for nome, detalhe in ferramentas_raw.items():
        ferramentas[nome] = _resumo_ferramenta(str(nome), detalhe)

    status_geral = "warning"
    if all(item.get("status") in {"success", "filtered", "no_data", "warning"} for item in ferramentas.values()):
        status_geral = "warning"
    if any(item.get("status") in {"error", "timeout", "unavailable", "auth_required"} for item in ferramentas.values()):
        status_geral = "error"
    if any(item.get("status") == "success" for item in ferramentas.values()):
        status_geral = "success"

    return {
        "email": email,
        "gerado_em": gerado_em,
        "status_geral": status_geral,
        "score_exposicao": _calcular_score_exposicao({"ferramentas": ferramentas}),
        "ferramentas": ferramentas,
    }


def carregar_dados(caminho_json: str | Path) -> dict[str, Any]:
    """Lê qualquer arquivo JSON no formato do Sentinela Digital."""
    with open(caminho_json, "r", encoding="utf-8") as handle:
        dados = json.load(handle)
    return dados


def _status_color(status: str) -> str:
    palette = {
        "success": colors.HexColor("#1E9E58"),
        "warning": colors.HexColor("#F59E0B"),
        "filtered": colors.HexColor("#9CA3AF"),
        "skipped": colors.HexColor("#64748B"),
        "no_data": colors.HexColor("#6B7280"),
        "error": colors.HexColor("#D64545"),
        "timeout": colors.HexColor("#F97316"),
        "unavailable": colors.HexColor("#EF4444"),
        "auth_required": colors.HexColor("#DC2626"),
        "unknown": colors.HexColor("#94A3B8"),
    }
    return palette.get(status.lower(), colors.HexColor("#7DD3FC"))


def _diagnostico_score(score: int) -> tuple[str, str]:
    if score <= 25:
        return "Baixa exposição", "#DCFCE7"
    if score <= 60:
        return "Exposição moderada", "#FEF3C7"
    return "Exposição elevada", "#FEE2E2"


def _nivel_risco_geral(resumo: dict[str, Any]) -> tuple[str, list[str], int, int]:
    ferr = resumo.get("ferramentas", {})
    contas_ativas = 0
    credenciais_vazadas = 0
    vetores: list[str] = []

    for nome, detalhe in ferr.items():
        if not isinstance(detalhe, dict):
            continue
        status = str(detalhe.get("status", "unknown")).lower()
        destaques = detalhe.get("destaques", []) or []
        contas_ativas += len(destaques)
        for linha in destaques:
            if "@" in linha or "password" in linha.lower() or "senha" in linha.lower():
                credenciais_vazadas += 1
        if status in {"error", "timeout", "unavailable", "auth_required"}:
            vetores.append(f"{nome}: falha de varredura ou autenticação incompleta.")
        elif status in {"success", "warning"} and destaques:
            vetores.append(f"{nome}: contas ou serviços relevantes foram localizados.")

    if credenciais_vazadas >= 3 or contas_ativas >= 3 or len(vetores) >= 3:
        nivel = "ALTO"
    elif credenciais_vazadas > 0 or contas_ativas > 0 or len(vetores) >= 1:
        nivel = "MÉDIO"
    else:
        nivel = "BAIXO"

    return nivel, vetores[:6], contas_ativas, credenciais_vazadas


def _montar_tabela_ferramentas(resumo: dict[str, Any]) -> list[list[str]]:
    linhas = [["Ferramenta", "Status", "Resumo"]]
    for nome, detalhe in resumo["ferramentas"].items():
        linhas.append([nome, detalhe.get("status", "unknown").upper(), detalhe.get("resumo", "Sem resumo")[:90]])
    return linhas


def _montar_destaques(resumo: dict[str, Any]) -> list[str]:
    destaques: list[str] = []
    for nome, detalhe in resumo["ferramentas"].items():
        for item in detalhe.get("destaques", []):
            linha = f"{nome}: {item}"
            if linha not in destaques:
                destaques.append(linha)
    return destaques[:12]


def _status_distribution(resumo: dict[str, Any]) -> list[int]:
    safe = 0
    found = 0
    failed = 0
    for detalhe in resumo["ferramentas"].values():
        status = str(detalhe.get("status", "unknown")).lower()
        if status in {"success", "filtered", "skipped", "no_data"}:
            safe += 1
        elif status in {"warning"}:
            found += 1
        elif status in {"error", "timeout", "unavailable", "auth_required"}:
            failed += 1
        else:
            safe += 1
    return [safe, found, failed]


def _adicionar_marca_dagua(canvas_obj, caminho_imagem: str | None = None, alpha: float = 0.08):
    if not caminho_imagem or not Path(caminho_imagem).exists():
        return
    try:
        canvas_obj.saveState()
        canvas_obj.setStrokeColor(colors.HexColor("#00D2FF"))
        canvas_obj.setFillColor(colors.HexColor("#00D2FF"))
        canvas_obj.setFillAlpha(alpha)
        canvas_obj.drawImage(caminho_imagem, 30 * mm, 50 * mm, width=160 * mm, height=220 * mm, preserveAspectRatio=True)
        canvas_obj.restoreState()
    except Exception:
        return


def _build_pie_chart(resumo: dict[str, Any]) -> Drawing:
    safe, found, failed = _status_distribution(resumo)
    drawing = Drawing(300, 200)
    chart = Pie()
    chart.x = 80
    chart.y = 15
    chart.width = 150
    chart.height = 150
    chart.data = [safe or 1, found or 1, failed or 1]
    chart.labels = ["Seguro", "Contas Encontradas", "Falha de Varredura"]
    chart.strokeWidth = 1
    chart.strokeColor = colors.white
    chart.slices.fontName = "Helvetica-Bold"
    chart.slices.fontSize = 7
    chart.slices.labelRadius = 1.05
    chart.slices[0].fillColor = colors.HexColor("#16A34A")
    chart.slices[1].fillColor = colors.HexColor("#F59E0B")
    chart.slices[2].fillColor = colors.HexColor("#DC2626")
    drawing.add(chart)
    return drawing


def _capa_executiva(elements: list[Any], resumo: dict[str, Any]) -> None:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0B172A"),
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.HexColor("#0F172A"),
        alignment=1,
    )
    meta_style = ParagraphStyle(
        "CoverMeta",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=10,
        textColor=colors.HexColor("#334155"),
        alignment=1,
    )
    confidential_style = ParagraphStyle(
        "Confidential",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=colors.HexColor("#991B1B"),
        alignment=1,
    )

    elements.append(Spacer(1, 25))
    elements.append(Paragraph("RELATÓRIO EXECUTIVO DE INTELIGÊNCIA OSINT", title_style))
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("SENTINELA DIGITAL", subtitle_style))
    elements.append(Spacer(1, 24))
    elements.append(Paragraph(f"Alvo: {resumo['email']}", meta_style))
    elements.append(Paragraph(f"Telemetria: {resumo['gerado_em']}", meta_style))
    elements.append(Paragraph(f"Status: {resumo['status_geral'].upper()}", meta_style))
    elements.append(Paragraph("Confidencial", confidential_style))
    elements.append(Spacer(1, 35))
    elements.append(Paragraph("Análise executiva de exposição digital e riscos de identidade.", meta_style))
    elements.append(PageBreak())


def _rodape_pagina(canvas_obj, total_pages: int | None = None) -> None:
    canvas_obj.saveState()
    canvas_obj.setFont("Helvetica", 8)
    canvas_obj.setFillColor(colors.HexColor("#475569"))
    pagina_atual = canvas_obj.getPageNumber()
    total = total_pages if total_pages is not None else pagina_atual
    canvas_obj.drawRightString(letter[0] - 45, 20, f"Página {pagina_atual} de {total}")
    canvas_obj.drawString(45, 20, "Confidencial — Sentinela Digital")
    canvas_obj.restoreState()


def _montar_pdf(dados: dict[str, Any], arquivo_saida_pdf: str | Path) -> None:
    resumo = _resumo_executivo(dados)
    score = resumo["score_exposicao"]
    diagnostico, bg_color = _diagnostico_score(score)
    nivel_risco, vetores, contas_ativas, credenciais_vazadas = _nivel_risco_geral(resumo)

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("TituloExecutivo", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, textColor=colors.HexColor("#0B192C"), leading=22)
    cabecalho = ParagraphStyle("Cabecalho", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=14, textColor=colors.HexColor("#0B192C"), leading=20)
    texto_box = ParagraphStyle("BoxText", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#0F172A"), leading=16)
    note_style = ParagraphStyle("Note", parent=styles["BodyText"], fontName="Helvetica", fontSize=10, textColor=colors.HexColor("#334155"), leading=14)

    doc = SimpleDocTemplate(
        str(arquivo_saida_pdf),
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=42,
        canvasmaker=NumberedCanvas,
    )
    elements: list[Any] = []

    _capa_executiva(elements, resumo)

    elements.append(Paragraph("Sentinela Digital — Relatório Executivo", titulo))
    elements.append(Spacer(1, 8))

    diag_table = Table(
        [[Paragraph("Diagnóstico", texto_box), Paragraph(f"Score de Exposição: {score}/100", texto_box), Paragraph(diagnostico, texto_box)]],
        colWidths=[130, 210, 170],
    )
    diag_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(bg_color)),
                ("GRID", (0, 0), (-1, -1), 1.2, colors.HexColor("#0F172A")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(diag_table)
    elements.append(Spacer(1, 14))

    risco_table = Table(
        [
            [Paragraph("Nível de Risco Geral", texto_box), Paragraph(nivel_risco, texto_box)],
            [Paragraph("Credenciais Vazadas", note_style), Paragraph(str(credenciais_vazadas), note_style)],
            [Paragraph("Contas Ativas Mapeadas", note_style), Paragraph(str(contas_ativas), note_style)],
        ],
        colWidths=[220, 220],
    )
    risco_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E2E8F0")),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(Paragraph("Avaliação de Riscos por Severidade", cabecalho))
    elements.append(risco_table)
    elements.append(Spacer(1, 10))

    if vetores:
        elements.append(Paragraph("Vetores de Risco Identificados", cabecalho))
        for item in vetores:
            elements.append(Paragraph(f"• {item}", note_style))
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("Proporção do Status das Ferramentas", cabecalho))
    elements.append(_build_pie_chart(resumo))
    elements.append(Spacer(1, 14))

    elements.append(Paragraph(f"Alvo: {resumo['email']}", styles["Normal"]))
    elements.append(Paragraph(f"Gerado em: {resumo['gerado_em']}", styles["Normal"]))
    elements.append(Paragraph(f"Status Geral: {resumo['status_geral'].upper()}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    tabela = Table(_montar_tabela_ferramentas(resumo), colWidths=[90, 70, 330])
    tabela.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0B192C")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#94A3B8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    for idx, row in enumerate(tabela._cellvalues[1:], start=1):
        status = row[1].lower()
        status_fill = {
            "success": colors.HexColor("#DCFCE7"),
            "warning": colors.HexColor("#FEF3C7"),
            "filtered": colors.HexColor("#E5E7EB"),
            "skipped": colors.HexColor("#E2E8F0"),
            "no_data": colors.HexColor("#E5E7EB"),
            "error": colors.HexColor("#FEE2E2"),
            "timeout": colors.HexColor("#FFEDD5"),
            "unavailable": colors.HexColor("#FEE2E2"),
            "auth_required": colors.HexColor("#FEE2E2"),
            "unknown": colors.HexColor("#E2E8F0"),
        }.get(status, colors.HexColor("#E2E8F0"))
        tabela.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, idx), (-1, idx), status_fill),
                    ("TEXTCOLOR", (1, idx), (1, idx), _status_color(status)),
                    ("FONTNAME", (1, idx), (1, idx), "Helvetica-Bold"),
                ]
            )
        )
    elements.append(Paragraph("Matriz de Ferramentas OSINT", cabecalho))
    elements.append(tabela)
    elements.append(Spacer(1, 18))

    destaques = _montar_destaques(resumo)
    if destaques:
        elementos_lista = []
        for item in destaques:
            elementos_lista.append(Paragraph(f"• {item}", styles["BodyText"]))
        elements.append(Paragraph("Destaques de Segurança", cabecalho))
        elements.extend(elementos_lista)
        elements.append(Spacer(1, 12))

    elements.append(Paragraph("Plano de Ação e Recomendações", cabecalho))
    elements.append(Paragraph("• Revisar credenciais expostas em serviços públicos e verificar contas ativas reportadas.", styles["BodyText"]))
    elements.append(Paragraph("• Validar autenticação do Google/GHunt e renovar cookies quando necessário.", styles["BodyText"]))
    elements.append(Paragraph("• Aplicar políticas de higiene digital: exclusão de contas abandonadas e monitoramento de vazamentos.", styles["BodyText"]))

    watermark_path = Path(__file__).resolve().parent / "IMG-20260909-WA6745.jpg"

    def _on_cover_page(canvas_obj, doc_obj):
        _rodape_pagina(canvas_obj)

    def _on_content_page(canvas_obj, doc_obj):
        _adicionar_marca_dagua(canvas_obj, str(watermark_path), alpha=0.05)
        _rodape_pagina(canvas_obj)

    doc.build(elements, onFirstPage=_on_cover_page, onLaterPages=_on_content_page)


def gerar_pdf(caminho_json: str | Path, arquivo_saida_pdf: str | Path) -> str:
    dados = carregar_dados(caminho_json)
    _montar_pdf(dados, arquivo_saida_pdf)
    caminho = str(Path(arquivo_saida_pdf))
    print(f"PDF gerado com sucesso: {caminho}")
    return caminho


def _main_cli() -> None:
    if len(sys.argv) not in {2, 3}:
        print("Uso: python pdf_generator.py <caminho_json> [caminho_pdf_saida]")
        raise SystemExit(1)

    json_input = sys.argv[1]
    pdf_output = sys.argv[2] if len(sys.argv) == 3 else str(Path(json_input).with_suffix(".pdf"))
    gerar_pdf(json_input, pdf_output)


if __name__ == "__main__":
    _main_cli()