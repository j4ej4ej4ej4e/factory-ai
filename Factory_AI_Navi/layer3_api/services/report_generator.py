"""
layer3_api/services/report_generator.py
=========================================
Factory AI Navi — PDF 레포트 생성 서비스 (ReportLab)
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── 색상 팔레트 ─────────────────────────────────
NAVY   = colors.HexColor("#1E3A5F")
BLUE   = colors.HexColor("#2563EB")
LIGHT  = colors.HexColor("#EFF6FF")
GRAY   = colors.HexColor("#6B7280")
GREEN  = colors.HexColor("#059669")
ORANGE = colors.HexColor("#D97706")
WHITE  = colors.white
BLACK  = colors.black


def generate_pdf(report: dict) -> bytes:
    """
    진단 결과 dict → PDF bytes 변환.

    Parameters
    ----------
    report : dict
        orchestrator 또는 report_cache에 저장된 진단 결과

    Returns
    -------
    bytes
        PDF 파일 바이트
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = _build_styles()
    story = []

    # ── 헤더 ────────────────────────────────────
    story += _header(report, styles)
    story.append(Spacer(1, 6*mm))

    # ── 1. 기업 개요 ────────────────────────────
    story += _section("1. 기업 개요", styles)
    story += _company_table(report, styles)
    story.append(Spacer(1, 5*mm))

    # ── 2. 동종업계 벤치마크 갭 분석 ────────────
    story += _section("2. 동종업계 벤치마크 갭 분석", styles)
    story += _gap_table(report, styles)
    story.append(Spacer(1, 5*mm))

    # ── 3. AI 적용 우선순위 ──────────────────────
    story += _section("3. AI 적용 우선순위 Top3", styles)
    story += _ai_priority_tables(report, styles)
    story.append(Spacer(1, 5*mm))

    # ── 4. ROI 시뮬레이션 ───────────────────────
    story += _section("4. ROI 시뮬레이션", styles)
    story += _roi_table(report, styles)
    story.append(Spacer(1, 5*mm))

    # ── 5. 추천 지원사업 ─────────────────────────
    story += _section("5. 추천 정부지원사업 Top5", styles)
    story += _subsidy_table(report, styles)
    story.append(Spacer(1, 5*mm))

    # ── 푸터 ────────────────────────────────────
    story += _footer(styles)

    doc.build(story)
    return buf.getvalue()


# ──────────────────────────────────────────────
# 스타일
# ──────────────────────────────────────────────

def _build_styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title", parent=base["Title"],
            fontSize=20, textColor=WHITE, alignment=TA_CENTER, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle", parent=base["Normal"],
            fontSize=11, textColor=LIGHT, alignment=TA_CENTER,
        ),
        "section": ParagraphStyle(
            "section", parent=base["Heading2"],
            fontSize=12, textColor=NAVY, spaceAfter=3, spaceBefore=3,
            borderPad=2,
        ),
        "body": ParagraphStyle(
            "body", parent=base["Normal"],
            fontSize=9, textColor=BLACK, leading=14,
        ),
        "small": ParagraphStyle(
            "small", parent=base["Normal"],
            fontSize=8, textColor=GRAY,
        ),
        "bold": ParagraphStyle(
            "bold", parent=base["Normal"],
            fontSize=9, textColor=BLACK, fontName="Helvetica-Bold",
        ),
    }


# ──────────────────────────────────────────────
# 섹션 빌더
# ──────────────────────────────────────────────

def _header(report: dict, s: dict) -> list:
    company = report.get("company", {})
    size_label = "소기업 (50인 미만)" if company.get("company_size") == "small" else "중기업 (50~300인)"

    header_data = [[
        Paragraph(f"<b>Factory AI Navi</b>", s["title"]),
    ]]
    header_table = Table(header_data, colWidths=[170*mm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))

    sub_data = [[Paragraph(
        f"AI 공정 진단 & 정부지원 매칭 레포트 | "
        f"{report.get('industry_name', '')} | {size_label} | "
        f"{datetime.now().strftime('%Y-%m-%d')}",
        s["subtitle"]
    )]]
    sub_table = Table(sub_data, colWidths=[170*mm])
    sub_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    return [header_table, sub_table]


def _section(title: str, s: dict) -> list:
    return [
        HRFlowable(width="100%", thickness=1, color=NAVY),
        Paragraph(title, s["section"]),
    ]


def _company_table(report: dict, s: dict) -> list:
    company = report.get("company", {})
    data = [
        ["항목", "입력값", "항목", "입력값"],
        ["업종", report.get("industry_name", "-"), "기업 규모", "소기업" if company.get("company_size") == "small" else "중기업"],
        ["종업원 수", f"{company.get('headcount', 0)}인", "연간 생산액", f"{company.get('annual_production', 0):,.0f}만원"],
        ["불량률", f"{company.get('defect_rate', '-')}%", "설비 가동률", f"{company.get('operating_rate', '-')}%"],
        ["에너지 비용", f"{company.get('energy_cost_ratio', '-')}%", "설비 노후도", f"{company.get('equipment_age', '-')}년"],
    ]
    t = Table(data, colWidths=[35*mm, 50*mm, 35*mm, 50*mm])
    t.setStyle(_base_table_style())
    return [t]


def _gap_table(report: dict, s: dict) -> list:
    gaps = report.get("gap_analysis", {})
    if not gaps:
        return [Paragraph("벤치마크 데이터 없음 (seed_db.py 실행 필요)", s["small"])]

    data = [["지표", "귀사 값", "동종평균", "갭", "평가"]]
    for key, g in gaps.items():
        if key == "ai_adoption_rate":
            continue
        unit = g.get("unit", "")
        gap_val = g.get("gap_pp") or g.get("gap_pct")
        gap_str = f"{gap_val:+.2f}{unit}" if gap_val is not None else "-"
        data.append([
            g.get("label", key),
            f"{g.get('company', '-')}{unit}",
            f"{g.get('peer_avg', '-')}{unit}",
            gap_str,
            g.get("assessment", "-"),
        ])

    t = Table(data, colWidths=[35*mm, 30*mm, 30*mm, 30*mm, 45*mm])
    t.setStyle(_base_table_style())
    return [t]


def _ai_priority_tables(report: dict, s: dict) -> list:
    priorities = report.get("ai_priorities", [])
    if not priorities:
        return [Paragraph("AI 우선순위 데이터 없음", s["small"])]

    elements = []
    for p in priorities[:3]:
        data = [
            [f"#{p.get('rank', '?')} {p.get('ai_name', '-')}", ""],
            ["적용 공정", p.get("target_process", "-")],
            ["기대 효과", p.get("expected_effect", "-")],
            ["구현 기간", p.get("implementation_period", "-")],
            ["예상 비용", f"{p.get('estimated_cost', 0):,}만원"],
            ["선정 근거", p.get("rationale", "-")],
        ]
        t = Table(data, colWidths=[40*mm, 130*mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("SPAN", (0, 0), (1, 0)),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("BACKGROUND", (0, 1), (0, -1), LIGHT),
            ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 3*mm))

    return elements


def _roi_table(report: dict, s: dict) -> list:
    roi_list = report.get("roi_results", [])
    if not roi_list:
        return [Paragraph("ROI 데이터 없음", s["small"])]

    data = [["AI 유형", "총 구축비", "자부담", "연간 절감", "회수기간", "3년 순이익", "ROI"]]
    for r in roi_list:
        data.append([
            r.get("ai_name", "-"),
            r.get("implementation_cost", "-"),
            r.get("net_investment", "-"),
            r.get("total_annual_savings", "-"),
            r.get("payback_months", "-"),
            r.get("three_year_profit", "-"),
            r.get("roi_pct", "-"),
        ])

    t = Table(data, colWidths=[30*mm, 25*mm, 22*mm, 25*mm, 20*mm, 28*mm, 20*mm])
    t.setStyle(_base_table_style())
    return [t]


def _subsidy_table(report: dict, s: dict) -> list:
    subsidies = report.get("subsidies", [])
    if not subsidies:
        return [Paragraph("지원사업 데이터 없음", s["small"])]

    data = [["#", "사업명", "최대 지원금", "자부담", "마감일"]]
    for i, sub in enumerate(subsidies[:5], 1):
        amount = f"{sub.get('max_support_amount', 0):,}만원" if sub.get("max_support_amount") else "-"
        co_rate = f"{sub.get('co_funding_rate', 0)*100:.0f}%" if sub.get("co_funding_rate") is not None else "-"
        data.append([
            str(i),
            sub.get("program_name", "-"),
            amount,
            co_rate,
            sub.get("application_end", "-"),
        ])

    t = Table(data, colWidths=[8*mm, 80*mm, 28*mm, 20*mm, 34*mm])
    t.setStyle(_base_table_style())
    return [t]


def _footer(s: dict) -> list:
    text = (
        "본 레포트는 KIAT 산업기술통계 / 고용노동부 인건비 통계 / 로봇산업진흥원 실태조사 기반 "
        "수치를 활용한 AI 분석 결과입니다. 실제 투자 결정 시 전문가 자문을 병행하시기 바랍니다."
    )
    return [
        HRFlowable(width="100%", thickness=0.5, color=GRAY),
        Spacer(1, 2*mm),
        Paragraph(text, s["small"]),
        Paragraph("© 2026 Factory AI Navi | datacontest.kr 제출용", s["small"]),
    ]


def _base_table_style() -> TableStyle:
    return TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ])
