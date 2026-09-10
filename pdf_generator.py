#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sentinela Digital — Gerador de Relatório Executivo em PDF
=========================================================

Lê dinamicamente qualquer relatório JSON produzido pelo Sentinela Digital
(``relatorio_mestre*.json``) e compila um PDF executivo refinado.

Uso:
    python pdf_generator.py <caminho_do_json> <caminho_do_pdf_saida>
                            [--analista "Nome"] [--watermark img.jpg]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# --------------------------------------------------------------------------- #
# Paleta Cyber / Executive
# --------------------------------------------------------------------------- #
NAVY = colors.HexColor("#0B192C")
NAVY_SOFT = colors.HexColor("#132A45")
CYAN = colors.HexColor("#00D2FF")
INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#4B5563")
LINE = colors.HexColor("#D6DEE8")
ZEBRA = colors.HexColor("#F3F7FB")
PAPER = colors.white

RED = colors.HexColor("#E03131")
ORANGE = colors.HexColor("#F08C00")
GREEN = colors.HexColor("#2F9E44")
GREY = colors.HexColor("#868E96")
BLUE = colors.HexColor("#1971C2")

STATUS_COLORS: Dict[str, colors.Color] = {
    "success": GREEN,
    "error": RED,
    "skipped": GREY,
    "rate_limited": ORANGE,
    "timeout": ORANGE,
    "partial": ORANGE,
    "unknown": BLUE,
}

STATUS_LABELS: Dict[str, str] = {
    "success": "SUCESSO",
    "error": "ERRO",
    "skipped": "IGNORADO",
    "rate_limited": "LIMITE TAXA",
    "timeout": "TIMEOUT",
    "partial": "PARCIAL",
    "unknown": "DESCONHECIDO",
}

SEVERITY_COLORS: Dict[str, colors.Color] = {
    "CRÍTICO": RED,
    "ALTO": colors.HexColor("#E8590C"),
    "MÉDIO": ORANGE,
    "BAIXO": GREEN,
    "INFORMATIVO": BLUE,
}

CONFIDENTIAL_STAMP = "CONFIDENCIAL — USO INTERNO RESTRITO"
SYSTEM_NAME = "Sentinela Digital"

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def _register_unicode_fonts() -> None:
    """Registra DejaVu Sans quando disponível (acentuação PT-BR segura)."""
    global FONT_REGULAR, FONT_BOLD
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for regular, bold in candidates:
        if os.path.exists(regular) and os.path.exists(bold):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", regular))
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold))
                FONT_REGULAR, FONT_BOLD = "DejaVuSans", "DejaVuSans-Bold"
            except Exception:
                pass
            return


# --------------------------------------------------------------------------- #
# Parsing e Saneamento do JSON
# --------------------------------------------------------------------------- #
FALSE_POSITIVE_HOSTS = {
    "discord.com",
    "api.mojang.com",
    "cavalier.hudsonrock.com",
    "rarible.com",
}


def clean_raw_message(text: str) -> str:
    """Sanitiza mensagens brutas removendo marcadores CLI e formatações indesejadas."""
    if not text:
        return ""
    # Remove marcadores comuns de CLI
    cleaned = re.sub(r"^\s*(\[\d+\]|\[\s*\]|\[!\]|\[\+\]|\[-\]|\[x\]|\[~\])\s*", "", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _lines(tool: Dict[str, Any]) -> List[str]:
    data = tool.get("data") or {}
    raw = data.get("lines") or []
    return [str(item) for item in raw]


def _fmt_datetime(value: Optional[str]) -> str:
    if not value:
        return "n/d"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.strftime("%d/%m/%Y %H:%M:%S UTC")


def parse_holehe(tool: Dict[str, Any]) -> List[str]:
    found = []
    for line in _lines(tool):
        match = re.match(r"^\s*\[\+\]\s*(\S+)", line)
        if not match:
            continue
        token = match.group(1).strip().rstrip(",;")
        if "." not in token or token.lower() in {"email", "used"}:
            continue
        found.append(token)
    return sorted(set(found))


def parse_sherlock(tool: Dict[str, Any], email: str) -> Tuple[List[Tuple[str, str]], int]:
    email_is_username = "@" in (email or "")
    valid: List[Tuple[str, str]] = []
    discarded = 0
    for line in _lines(tool):
        match = re.match(r"^\s*\[\+\]\s*([^:]+):\s*(\S+)", line)
        if not match:
            continue
        site, url = match.group(1).strip(), match.group(2).strip()
        host = re.sub(r"^https?://", "", url).split("/")[0].lower()
        if email_is_username or host in FALSE_POSITIVE_HOSTS:
            discarded += 1
            continue
        valid.append((site, url))
    return valid, discarded


def parse_h8mail(tool: Dict[str, Any]) -> Tuple[str, List[str]]:
    verdict = "Sem resultados"
    errors: List[str] = []
    for line in _lines(tool):
        low = line.lower()
        if "not compromised" in low:
            verdict = "Não comprometido nas fontes consultadas"
        elif "compromised" in low and "not compromised" not in low:
            verdict = "Indício de comprometimento reportado"
        if line.strip().startswith("[!]") and "error" in low:
            errors.append(clean_raw_message(line))
    return verdict, errors


def parse_failures(tool_name: str, tool: Dict[str, Any]) -> List[str]:
    data = tool.get("data") or {}
    messages: List[str] = []
    if data.get("warning"):
        messages.append(clean_raw_message(str(data["warning"])))
    if data.get("reason"):
        messages.append(clean_raw_message(str(data["reason"])))
    for line in _lines(tool):
        stripped = clean_raw_message(line)
        if re.search(r"(ModuleNotFoundError|Traceback|No module named|Invalid command|"
                      r"Invalid module name|Invalid option name|Invalid workspace|"
                      r"rate limit|is down|error:|command not found|Permission denied)",
                      stripped, re.IGNORECASE):
            messages.append(stripped)
    seen, unique = set(), []
    for message in messages:
        key = message[:160]
        if key not in seen:
            seen.add(key)
            unique.append(message)
    return unique[:6]


# --------------------------------------------------------------------------- #
# Motor de Risco
# --------------------------------------------------------------------------- #
RISK_RULES: List[Dict[str, Any]] = [
    {
        "match": r"No module named|ModuleNotFoundError|Traceback",
        "titulo": "Dependência Python ausente",
        "impacto": "Coleta incompleta e superfície de exposição do alvo subestimada.",
        "severidade": "ALTO",
        "probabilidade": "Alta",
        "riscos": "Falso negativo operacional; decisões baseadas em telemetria parcial.",
        "mitigacao": "Fixar dependências no requirements.txt e validar via healthcheck.",
    },
    {
        "match": r"cookies|GHUNT_COOKIES_FILE",
        "titulo": "Sessão / Credencial ausente",
        "impacto": "Módulos com autenticação não executam, limitando o enriquecimento.",
        "severidade": "MÉDIO",
        "probabilidade": "Alta",
        "riscos": "Cobertura reduzida de inteligência de identidade.",
        "mitigacao": "Armazenar cookies/chaves em cofre seguro (.env / Vault) com rotação.",
    },
    {
        "match": r"rate limit|rate_limited|429",
        "titulo": "Bloqueio por limite de taxa",
        "impacto": "Enumeração interrompida antes da conclusão da varredura.",
        "severidade": "MÉDIO",
        "probabilidade": "Alta",
        "riscos": "Resultados parciais e possível bloqueio de IP da infraestrutura.",
        "mitigacao": "Aplicar backoff exponencial e rotação de IP via proxy/VPN.",
    },
    {
        "match": r"Invalid command|Invalid module|Invalid option|Invalid workspace",
        "titulo": "Incompatibilidade de versão",
        "impacto": "Scanner finaliza sem erro mas não executa os comandos corretos.",
        "severidade": "ALTO",
        "probabilidade": "Alta",
        "riscos": "Sensação falsa de cobertura sem a coleta efetiva de dados.",
        "mitigacao": "Ajustar parâmetros para a versão exata do software no pipeline.",
    },
    {
        "match": r"api key|api_key|hunter\.io|apikey|missing key",
        "titulo": "Chave de API ausente/inválida",
        "impacto": "Consultas em bases pagas ou restritas são abortadas.",
        "severidade": "ALTO",
        "probabilidade": "Média",
        "riscos": "Vazamentos conhecidos em fontes pagas passam sem detecção.",
        "mitigacao": "Provisionar e monitorar validade das chaves de API ativas.",
    },
    {
        "match": r"is down|skipping|timeout|unreachable",
        "titulo": "Fonte externa indisponível",
        "impacto": "Instabilidade temporária na base de consulta do provedor.",
        "severidade": "BAIXO",
        "probabilidade": "Média",
        "riscos": "Inconsistência pontual na janela da varredura.",
        "mitigacao": "Agendar reexecução automática para as fontes indisponíveis.",
    },
]

FALLBACK_RISK = {
    "titulo": "Falha operacional de coleta",
    "impacto": "Etapa de varredura não concluída conforme o esperado.",
    "severidade": "MÉDIO",
    "probabilidade": "Média",
    "riscos": "Lacuna pontual de evidência no relatório.",
    "mitigacao": "Revisar logs brutos da ferramenta e reexecutar individualmente.",
}


def classify_failure(message: str) -> Dict[str, Any]:
    for rule in RISK_RULES:
        if re.search(rule["match"], message, re.IGNORECASE):
            return rule
    return FALLBACK_RISK


def build_findings(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    email = report.get("email", "")
    tools: Dict[str, Any] = report.get("ferramentas") or {}
    findings: List[Dict[str, Any]] = []

    for name in sorted(tools):
        tool = tools[name] or {}
        status = str(tool.get("status", "unknown")).lower()
        messages = parse_failures(name, tool)
        if status in ("success",) and not messages:
            continue
        if not messages:
            messages = [f"Ferramenta finalizada com status '{status}'."]
        for message in messages[:2]:
            rule = classify_failure(message)
            findings.append({
                "origem": name,
                "titulo": rule["titulo"],
                "evidencia": message,
                "impacto": rule["impacto"],
                "severidade": rule["severidade"],
                "probabilidade": rule["probabilidade"],
                "riscos": rule["riscos"],
                "mitigacao": rule["mitigacao"],
            })

    holehe_hits = parse_holehe(tools.get("holehe", {}))
    if holehe_hits:
        findings.append({
            "origem": "holehe",
            "titulo": f"Alvo registrado em {len(holehe_hits)} serviço(s)",
            "evidencia": ", ".join(holehe_hits[:10]) + ("…" if len(holehe_hits) > 10 else ""),
            "impacto": "Superfície exposta ampliada em serviços de terceiros.",
            "severidade": "ALTO" if len(holehe_hits) > 5 else "MÉDIO",
            "probabilidade": "Alta",
            "riscos": "Riscos de engenharia social direcionada e reset de conta.",
            "mitigacao": "Ativar MFA em todos os serviços e gerenciar senhas salvas.",
        })

    if "h8mail" in tools:
        verdict, api_errors = parse_h8mail(tools["h8mail"])
        if "comprometimento" in verdict.lower():
            findings.append({
                "origem": "h8mail",
                "titulo": "Credencial presente em base de vazamentos",
                "evidencia": verdict,
                "impacto": "Acesso potencial a contas que reutilizem a mesma senha.",
                "severidade": "CRÍTICO",
                "probabilidade": "Alta",
                "riscos": "Tomada de conta imediata e ataques de credential stuffing.",
                "mitigacao": "Troca imediata de credenciais e ativação de MFA.",
            })

    _, discarded = parse_sherlock(tools.get("sherlock", {}), email)
    if discarded:
        findings.append({
            "origem": "sherlock",
            "titulo": f"{discarded} falso(s) positivo(s) descartado(s)",
            "evidencia": "URL apenas ecoa a string do e-mail sem validar perfil ativo.",
            "impacto": "Sem impacto direto no alvo após aplicação do filtro.",
            "severidade": "INFORMATIVO",
            "probabilidade": "Alta",
            "riscos": "Desperdício de tempo em análises de perfis inexistentes.",
            "mitigacao": "Ajustar regex de verificação para o nome de usuário isolado.",
        })

    # Deduplicação
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for finding in findings:
        key = (finding["origem"], finding["titulo"])
        if key in merged:
            existing = merged[key]["evidencia"]
            extra = finding["evidencia"]
            if extra not in existing and len(existing) < 200:
                merged[key]["evidencia"] = f"{existing} | {extra}"
        else:
            merged[key] = finding
    
    order = {"CRÍTICO": 0, "ALTO": 1, "MÉDIO": 2, "BAIXO": 3, "INFORMATIVO": 4}
    res = list(merged.values())
    res.sort(key=lambda item: order.get(item["severidade"], 9))
    return res


# --------------------------------------------------------------------------- #
# Canvas Numerado e Estilizado
# --------------------------------------------------------------------------- #
class NumberedCanvas(rl_canvas.Canvas):
    watermark_path: Optional[str] = None
    watermark_alpha: float = 0.05
    header_title: str = SYSTEM_NAME
    header_subtitle: str = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._saved_states: List[Dict[str, Any]] = []

    def showPage(self) -> None:
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self) -> None:
        total = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            self._draw_watermark()
            self._draw_header()
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_watermark(self) -> None:
        if not self.watermark_path or not os.path.exists(self.watermark_path):
            return
        try:
            image = ImageReader(self.watermark_path)
            iw, ih = image.getSize()
        except Exception:
            return
        width, height = self._pagesize
        size = min(width, height) * 0.55
        draw_w, draw_h = size, size * ih / iw
        self.saveState()
        try:
            self.setFillAlpha(self.watermark_alpha)
            self.setStrokeAlpha(self.watermark_alpha)
        except Exception:
            pass
        self.drawImage(
            image,
            (width - draw_w) / 2.0,
            (height - draw_h) / 2.0,
            width=draw_w,
            height=draw_h,
            mask="auto",
        )
        self.restoreState()

    def _draw_header(self) -> None:
        width, height = self._pagesize
        band = 16 * mm
        self.saveState()
        self.setFillColor(NAVY)
        self.rect(0, height - band, width, band, stroke=0, fill=1)
        self.setFillColor(CYAN)
        self.rect(0, height - band - 1.2, width, 1.2, stroke=0, fill=1)
        self.setFillColor(colors.white)
        self.setFont(FONT_BOLD, 10)
        self.drawString(18 * mm, height - band + 5.5 * mm, self.header_title)
        self.setFillColor(CYAN)
        self.setFont(FONT_REGULAR, 7.8)
        self.drawRightString(width - 18 * mm, height - band + 5.5 * mm, CONFIDENTIAL_STAMP)
        self.restoreState()

    def _draw_footer(self, total: int) -> None:
        width, _ = self._pagesize
        self.saveState()
        self.setStrokeColor(LINE)
        self.setLineWidth(0.5)
        self.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
        self.setFont(FONT_REGULAR, 7.5)
        self.setFillColor(MUTED)
        self.drawString(18 * mm, 9.5 * mm, self.header_subtitle or SYSTEM_NAME)
        self.drawCentredString(width / 2.0, 9.5 * mm, CONFIDENTIAL_STAMP)
        self.setFillColor(NAVY)
        self.setFont(FONT_BOLD, 7.5)
        self.drawRightString(width - 18 * mm, 9.5 * mm, f"Página {self._pageNumber} de {total}")
        self.restoreState()


# --------------------------------------------------------------------------- #
# Estilos do Documento
# --------------------------------------------------------------------------- #
def build_styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    styles = {
        "title": ParagraphStyle(
            "SDTitle", parent=base["Title"], fontName=FONT_BOLD, fontSize=20,
            leading=24, textColor=NAVY, alignment=TA_CENTER, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "SDSubtitle", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=9,
            leading=12, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "SDH1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=11,
            leading=14, textColor=colors.white, spaceBefore=8, spaceAfter=5,
            backColor=NAVY, borderPadding=(4, 6, 4, 6),
        ),
        "h2": ParagraphStyle(
            "SDH2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=9.5,
            leading=12, textColor=NAVY, spaceBefore=6, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "SDBody", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=8.5,
            leading=11.5, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "SDSmall", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=7.5,
            leading=9.8, textColor=INK,
        ),
        "small_center": ParagraphStyle(
            "SDSmallCenter", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.2,
            leading=9.5, textColor=colors.white, alignment=TA_CENTER,
        ),
        "smallmuted": ParagraphStyle(
            "SDSmallMuted", parent=base["Normal"], fontName=FONT_REGULAR, fontSize=7.2,
            leading=9.2, textColor=MUTED,
        ),
        "cellhead": ParagraphStyle(
            "SDCellHead", parent=base["Normal"], fontName=FONT_BOLD, fontSize=7.8,
            leading=10, textColor=colors.white, alignment=TA_CENTER,
        ),
    }
    return styles


def section(title: str, styles: Dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(title.upper(), styles["h1"])


def kv_table(rows: Iterable[Tuple[str, str]], styles: Dict[str, ParagraphStyle], width: float) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", styles["small"]), Paragraph(v, styles["small"])] for k, v in rows]
    table = Table(data, colWidths=[0.30 * width, 0.70 * width], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), ZEBRA),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


# --------------------------------------------------------------------------- #
# Construção do PDF
# --------------------------------------------------------------------------- #
def build_story(report: Dict[str, Any], styles: Dict[str, ParagraphStyle],
                width: float, analista: str) -> List[Any]:
    email = report.get("email") or "n/d"
    tools: Dict[str, Any] = report.get("ferramentas") or {}
    findings = build_findings(report)
    holehe_hits = parse_holehe(tools.get("holehe", {}))
    _, sherlock_discarded = parse_sherlock(tools.get("sherlock", {}), email)
    h8_verdict, _ = parse_h8mail(tools.get("h8mail", {})) if "h8mail" in tools else ("n/d", [])

    counts: Dict[str, int] = {}
    for tool in tools.values():
        status = str((tool or {}).get("status", "unknown")).lower()
        counts[status] = counts.get(status, 0) + 1

    story: List[Any] = []

    # --- Header Executivo ---
    story.append(Spacer(1, 2))
    story.append(Paragraph("Relatório Executivo de Inteligência OSINT", styles["title"]))
    story.append(Paragraph(f"{SYSTEM_NAME} · Avaliação de exposição digital e postura de segurança", styles["subtitle"]))

    story.append(section("1. Cabeçalho Executivo", styles))
    story.append(kv_table([
        ("Alvo auditado", email),
        ("Telemetria (geração)", _fmt_datetime(report.get("gerado_em"))),
        ("Analista responsável", analista),
        ("Diretório da coleta", report.get("diretorio_scan") or "n/d"),
        ("Ferramentas executadas", str(len(tools))),
        ("Classificação", CONFIDENTIAL_STAMP),
    ], styles, width))

    story.append(Paragraph("Sumário da postura", styles["h2"]))
    summary_cells = [
        ("Ferramentas", str(len(tools)), NAVY),
        ("Sucesso", str(counts.get("success", 0)), GREEN),
        ("Falhas/limitações", str(sum(v for k, v in counts.items() if k != "success")), RED),
        ("Achados", str(len(findings)), CYAN),
        ("Contas confirmadas", str(len(holehe_hits)), ORANGE),
    ]
    header_row = [Paragraph(f"<b>{label}</b>", styles["cellhead"]) for label, _, _ in summary_cells]
    value_row = [Paragraph(f"<b>{value}</b>", styles["small"]) for _, value, _ in summary_cells]
    summary = Table([header_row, value_row], colWidths=[width / len(summary_cells)] * len(summary_cells))
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 1), (-1, 1), ZEBRA),
    ]
    for index, (_, _, color) in enumerate(summary_cells):
        cmds.append(("BACKGROUND", (index, 0), (index, 0), color))
    summary.setStyle(TableStyle(cmds))
    story.append(summary)

    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"A varredura consultou {len(tools)} scanners OSINT contra o alvo <b>{email}</b>. "
        f"Verificação de vazamentos: <b>{h8_verdict}</b>. Consolidados <b>{len(findings)} achados</b>. "
        f"Resultados genéricos descartados como falso positivo: {sherlock_discarded}.", styles["body"]
    ))

    # --- Seção 2: Matriz de Ferramentas ---
    story.append(section("2. Matriz de Ferramentas OSINT", styles))
    head = ["Ferramenta", "Status", "Código", "Observação"]
    data = [[Paragraph(f"<b>{h}</b>", styles["cellhead"]) for h in head]]
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (1, 1), (2, -1), "CENTER"),
    ]
    for row_index, name in enumerate(sorted(tools), start=1):
        tool = tools[name] or {}
        status = str(tool.get("status", "unknown")).lower()
        color = STATUS_COLORS.get(status, BLUE)
        label = STATUS_LABELS.get(status, status.upper())
        returncode = (tool.get("data") or {}).get("returncode")
        fallback = "Execução concluída sem erros." if status == "success" else "Sem mensagem detalhada; ver seção 4."
        note = (parse_failures(name, tool) or [fallback])[0]
        
        data.append([
            Paragraph(name, styles["small"]),
            Paragraph(f"<b>{label}</b>", styles["small_center"]),
            Paragraph("—" if returncode is None else str(returncode), styles["small"]),
            Paragraph(note[:180] + ("..." if len(note) > 180 else ""), styles["smallmuted"]),
        ])
        cmds.append(("BACKGROUND", (1, row_index), (1, row_index), color))
        if row_index % 2 == 0:
            cmds.append(("BACKGROUND", (0, row_index), (0, row_index), ZEBRA))
            cmds.append(("BACKGROUND", (2, row_index), (-1, row_index), ZEBRA))

    matrix = Table(data, colWidths=[0.20 * width, 0.16 * width, 0.09 * width, 0.55 * width], repeatRows=1)
    matrix.setStyle(TableStyle(cmds))
    story.append(matrix)

    # --- Seção 3: Destaques de Segurança ---
    story.append(section("3. Destaques de Segurança", styles))
    if holehe_hits:
        story.append(Paragraph(f"Contas confirmadas via Holehe ({len(holehe_hits)}):", styles["h2"]))
        columns = 3
        rows: List[List[Any]] = []
        for index in range(0, len(holehe_hits), columns):
            chunk = holehe_hits[index:index + columns]
            chunk += [""] * (columns - len(chunk))
            rows.append([Paragraph(item, styles["small"]) for item in chunk])
        hits = Table(rows, colWidths=[width / columns] * columns)
        hits.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.3, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PAPER, ZEBRA]),
        ]))
        story.append(hits)
    else:
        story.append(Paragraph("Nenhuma conta atrelada ao e-mail foi confirmada positivamente pelos módulos de consulta.", styles["body"]))

    # --- Seção 4: Matriz de Falhas e Riscos ---
    story.append(section("4. Falhas Encontradas, Impacto e Risco", styles))
    
    # Larguras EXATAS para evitar truncamento de rótulos
    # Total = 1.0 (530 pt)
    col_widths = [0.05 * width, 0.27 * width, 0.14 * width, 0.10 * width, 0.24 * width, 0.20 * width]
    
    f_head = ["#", "Achado / Origem", "Criticidade", "Prob.", "Impacto e Riscos", "Mitigação"]
    f_data = [[Paragraph(f"<b>{h}</b>", styles["cellhead"]) for h in f_head]]
    
    f_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("ALIGN", (0, 1), (0, -1), "CENTER"),
        ("ALIGN", (2, 1), (3, -1), "CENTER"),
    ]

    for idx, finding in enumerate(findings, start=1):
        sev = finding["severidade"]
        sev_color = SEVERITY_COLORS.get(sev, BLUE)
        
        origem_box = f"<b>{finding['titulo']}</b><br/><font color='{MUTED.hexval()}'>{finding['origem']}</font>"
        if finding["evidencia"]:
            origem_box += f"<br/><font color='{MUTED.hexval()}'><i>{finding['evidencia'][:120]}</i></font>"

        impacto_box = f"{finding['impacto']}<br/><b>Riscos:</b> {finding['riscos']}"

        f_data.append([
            Paragraph(str(idx), styles["small"]),
            Paragraph(origem_box, styles["small"]),
            Paragraph(f"<b>{sev}</b>", styles["small_center"]),
            Paragraph(finding["probabilidade"], styles["small"]),
            Paragraph(impacto_box, styles["small"]),
            Paragraph(finding["mitigacao"], styles["small"]),
        ])
        
        f_cmds.append(("BACKGROUND", (2, idx), (2, idx), sev_color))
        if idx % 2 == 0:
            f_cmds.append(("BACKGROUND", (0, idx), (1, idx), ZEBRA))
            f_cmds.append(("BACKGROUND", (3, idx), (-1, idx), ZEBRA))

    findings_table = Table(f_data, colWidths=col_widths, repeatRows=1)
    findings_table.setStyle(TableStyle(f_cmds))
    story.append(findings_table)

    # --- Seção 5: Plano de Ação ---
    story.append(section("5. Plano de Ação e Higiene Digital", styles))
    plan_data = [
        [Paragraph("<b>Horizonte</b>", styles["cellhead"]), Paragraph("<b>Ações Recomendadas</b>", styles["cellhead"])],
        [Paragraph("<b>Imediato (0-48h)</b>", styles["small"]), Paragraph("Trocar senhas dos serviços expostos e ativar Autenticação em Duas Etapas (MFA/TOTP).", styles["small"])],
        [Paragraph("<b>Curto Prazo (1-2 sem.)</b>", styles["small"]), Paragraph("Adotar gerenciador de senhas e encerrar contas inativas atreladas ao e-mail.", styles["small"])],
        [Paragraph("<b>Médio Prazo (30-90 dias)</b>", styles["small"]), Paragraph("Corrigir dependências e chaves do ambiente de coleta OSINT para eliminar lacunas.", styles["small"])],
        [Paragraph("<b>Contínuo</b>", styles["small"]), Paragraph("Monitoramento periódico de exposição de credenciais e auditoria de presença digital.", styles["small"])],
    ]
    plan_table = Table(plan_data, colWidths=[0.25 * width, 0.75 * width], repeatRows=1)
    plan_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAPER, ZEBRA]),
    ]))
    story.append(plan_table)

    return story


# --------------------------------------------------------------------------- #
# Indicadores de exposição para integrações legadas
# --------------------------------------------------------------------------- #
def _calcular_score_exposicao(report: Dict[str, Any]) -> int:
    """Calcula um score simples somente a partir de evidências confirmadas."""
    tools: Dict[str, Any] = report.get("ferramentas") or {}
    score = 0

    holehe_tool = tools.get("holehe", {}) or {}
    holehe_lines = _lines(holehe_tool)
    holehe_lines.extend(str(item) for item in holehe_tool.get("destaques") or [])
    holehe_hits = sorted({
        match.group(1).strip().rstrip(",;")
        for line in holehe_lines
        for match in [re.match(r"^\s*\[\+\]\s*(\S+)", line)]
        if match and "." in match.group(1) and match.group(1).lower() not in {"email", "used"}
    })
    score += min(len(holehe_hits), 10) * 10

    h8mail = tools.get("h8mail", {}) or {}
    h8_lines = " ".join(_lines(h8mail) + [str(item) for item in h8mail.get("destaques") or []]).lower()
    if re.search(r"compromised|breach", h8_lines) and not re.search(
        r"not compromised|no breach", h8_lines
    ):
        score += 40

    for name in ("gitleaks", "sherlock"):
        tool = tools.get(name, {}) or {}
        evidence = " ".join(_lines(tool)).lower()
        highlights = " ".join(str(item) for item in tool.get("destaques") or []).lower()
        combined = f"{evidence} {highlights}"
        if name == "gitleaks" and re.search(r"leak|secret|password|token", combined):
            if "no leak" not in combined and "nenhum vazamento" not in combined:
                score += 50
        if name == "sherlock" and parse_sherlock(tool, report.get("email", ""))[0]:
            score += 20

    return min(score, 100)


def _nivel_risco_geral(report: Dict[str, Any]) -> Tuple[str, List[str], int, int]:
    """Retorna nível, vetores confirmados, contas ativas e score."""
    tools: Dict[str, Any] = report.get("ferramentas") or {}
    score = _calcular_score_exposicao(report)
    holehe_tool = tools.get("holehe", {}) or {}
    holehe_evidence = _lines(holehe_tool) + [
        str(item) for item in holehe_tool.get("destaques") or []
    ]
    holehe_positive = [line for line in holehe_evidence if re.match(r"^\s*\[\+\]", line)]
    h8mail = tools.get("h8mail", {}) or {}
    h8_evidence = " ".join(
        _lines(h8mail) + [str(item) for item in h8mail.get("destaques") or []]
    ).lower()
    h8_confirmed = bool(re.search(r"compromised|breach", h8_evidence)) and not bool(
        re.search(r"not compromised|no breach", h8_evidence)
    )
    contas_ativas = len(holehe_positive) + (1 if h8_confirmed else 0)
    vetores: List[str] = []

    if contas_ativas:
        vetores.append(f"Holehe: {contas_ativas} conta(s) ativa(s) confirmada(s)")
    if h8_confirmed:
        vetores.append("H8mail: indício de comprometimento")
    sherlock_hits, _ = parse_sherlock(tools.get("sherlock", {}), report.get("email", ""))
    if sherlock_hits:
        vetores.append(f"Sherlock: {len(sherlock_hits)} perfil(is) confirmado(s)")

    if score >= 70:
        nivel = "CRÍTICO"
    elif score >= 30:
        nivel = "ALTO"
    elif score > 0:
        nivel = "MÉDIO"
    else:
        nivel = "BAIXO"
    return nivel, vetores, contas_ativas, score


# --------------------------------------------------------------------------- #
# Entrypoint Principal
# --------------------------------------------------------------------------- #
def generate_pdf(json_path: str, output_pdf_path: str, analista: str = "Equipe de Segurança", watermark: Optional[str] = None) -> str:
    json_path = str(json_path)
    output_pdf_path = str(output_pdf_path)
    _register_unicode_fonts()
    
    with open(json_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    doc = BaseDocTemplate(
        output_pdf_path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="normal",
        topPadding=0, bottomPadding=0, leftPadding=0, rightPadding=0
    )

    canvas_maker = NumberedCanvas
    canvas_maker.watermark_path = watermark or os.path.join("assets", "watermark.png")
    canvas_maker.header_subtitle = f"Alvo: {report.get('email', 'n/d')}"

    template = PageTemplate(id="Executive", frames=frame)
    doc.addPageTemplates([template])

    styles = build_styles()
    story = build_story(report, styles, doc.width, analista)

    doc.build(story, canvasmaker=canvas_maker)
    print(f"PDF executivo gerado com sucesso: {output_pdf_path}")
    return output_pdf_path


gerar_pdf = generate_pdf


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gerador de Relatórios Executivos em PDF — Sentinela Digital")
    parser.add_argument("json_path", help="Caminho do arquivo JSON de entrada")
    parser.add_argument("output_pdf", help="Caminho do arquivo PDF de saída")
    parser.add_argument("--analista", default="Equipe de Inteligência Cibernética", help="Nome do analista responsável")
    parser.add_argument("--watermark", default=None, help="Caminho da imagem de marca d'água")

    args = parser.parse_args()
    generate_pdf(args.json_path, args.output_pdf, args.analista, args.watermark)