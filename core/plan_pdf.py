"""Render the financial plan in SessionState to a premium PDF with reportlab.

Visual language matches the affluent UI tokens in web/src/index.css:
navy chrome + cream surfaces + champagne accent + serif display type.
"""

import os
import time

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .session import SessionState

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")

# Palette mirrors web/src/index.css :root tokens.
NAVY = colors.HexColor("#0A1628")
NAVY_SOFT = colors.HexColor("#161E2E")
NAVY_EDGE = colors.HexColor("#1F2940")
CREAM = colors.HexColor("#F7F2EA")
CREAM_DEEP = colors.HexColor("#EBE3D5")
CHAMPAGNE = colors.HexColor("#C9A961")
CHAMPAGNE_SOFT = colors.HexColor("#E1C589")
GREEN = colors.HexColor("#3D7C57")
GREEN_SOFT = colors.HexColor("#E0EDE5")
AMBER = colors.HexColor("#C9772A")
AMBER_SOFT = colors.HexColor("#F6E4D2")
INK = colors.HexColor("#1A1F2E")
INK_SOFT = colors.HexColor("#5D6478")
INK_FAINT = colors.HexColor("#9AA0AE")
IVORY = colors.HexColor("#F5EDDB")
IVORY_SOFT = colors.HexColor("#C9C2B0")
HAIRLINE = colors.HexColor("#E4DCCA")

PAGE_W, PAGE_H = A4
SIDE_MARGIN = 18 * mm
COVER_BAND_H = 46 * mm
HEADER_BAND_H = 14 * mm


def _inr(x: float | None) -> str:
    # Core PDF fonts (Helvetica/Times) lack the U+20B9 rupee glyph, so we stick
    # with the ASCII "Rs" prefix to avoid tofu boxes in the rendered PDF.
    if x is None:
        return "—"
    x = float(x)
    if x >= 1e7:
        return f"Rs {x / 1e7:.2f} Cr"
    if x >= 1e5:
        return f"Rs {x / 1e5:.1f} L"
    return f"Rs {x:,.0f}"


def _draw_cover_band(canvas: Canvas, state: SessionState) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - COVER_BAND_H, PAGE_W, COVER_BAND_H, fill=1, stroke=0)

    canvas.setFillColor(CHAMPAGNE)
    canvas.rect(0, PAGE_H - COVER_BAND_H - 1.2, PAGE_W, 1.2, fill=1, stroke=0)

    canvas.setFillColor(CHAMPAGNE)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(SIDE_MARGIN, PAGE_H - 14 * mm, "WEALTH  EXPERT")

    canvas.setFillColor(IVORY)
    canvas.setFont("Times-Roman", 28)
    canvas.drawString(SIDE_MARGIN, PAGE_H - 28 * mm, "Your Financial Plan")

    canvas.setFillColor(IVORY_SOFT)
    canvas.setFont("Helvetica", 9.5)
    subtitle = f"Prepared for {state.name or 'Client'}   •   {time.strftime('%d %B %Y')}"
    canvas.drawString(SIDE_MARGIN, PAGE_H - 36 * mm, subtitle)

    canvas.setFillColor(CHAMPAGNE)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(PAGE_W - SIDE_MARGIN, PAGE_H - 14 * mm, "CONFIDENTIAL")
    canvas.restoreState()


def _draw_header_band(canvas: Canvas) -> None:
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - HEADER_BAND_H, PAGE_W, HEADER_BAND_H, fill=1, stroke=0)

    canvas.setFillColor(CHAMPAGNE)
    canvas.rect(0, PAGE_H - HEADER_BAND_H - 0.8, PAGE_W, 0.8, fill=1, stroke=0)

    canvas.setFillColor(CHAMPAGNE)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(SIDE_MARGIN, PAGE_H - 9 * mm, "WEALTH  EXPERT")

    canvas.setFillColor(IVORY_SOFT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(PAGE_W - SIDE_MARGIN, PAGE_H - 9 * mm, "YOUR FINANCIAL PLAN")
    canvas.restoreState()


def _draw_footer(canvas: Canvas, page_num: int, client: str) -> None:
    canvas.saveState()
    canvas.setStrokeColor(CHAMPAGNE)
    canvas.setLineWidth(0.4)
    canvas.line(SIDE_MARGIN, 14 * mm, PAGE_W - SIDE_MARGIN, 14 * mm)

    canvas.setFillColor(INK_SOFT)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(SIDE_MARGIN, 10 * mm, f"Wealth Expert  •  Prepared for {client}")
    canvas.drawRightString(PAGE_W - SIDE_MARGIN, 10 * mm, f"Page {page_num}")
    canvas.restoreState()


class _AllocationBar(Flowable):
    """Equity / debt / gold horizontal bar with inline labels."""

    def __init__(self, equity: float, debt: float, gold: float, width: float = 130 * mm):
        super().__init__()
        self.equity = equity
        self.debt = debt
        self.gold = gold
        self.width = width
        self.height = 10

    def draw(self):
        c = self.canv
        x = 0
        for frac, color in (
            (self.equity, NAVY),
            (self.debt, INK_SOFT),
            (self.gold, CHAMPAGNE),
        ):
            w = max(0, self.width * frac)
            if w > 0:
                c.setFillColor(color)
                c.rect(x, 0, w, self.height, fill=1, stroke=0)
                x += w

    def wrap(self, *_):
        return (self.width, self.height)


def _section_heading(text: str, styles) -> list:
    return [
        Spacer(1, 6 * mm),
        Paragraph(text, styles["h2"]),
        HRFlowable(width=28 * mm, thickness=1.1, color=CHAMPAGNE,
                   spaceBefore=1, spaceAfter=3),
    ]


def _kpi_card(label: str, value: str, accent: colors.Color) -> Table:
    inner = Table(
        [
            [Paragraph(f"<font size=7 color='#5D6478'>{label.upper()}</font>", _BODY)],
            [Paragraph(f"<font size=15 color='#1A1F2E'><b>{value}</b></font>", _BODY)],
        ],
        colWidths=[52 * mm],
        rowHeights=[6 * mm, 12 * mm],
        style=TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), CREAM),
            ("LINEABOVE", (0, 0), (-1, 0), 2.4, accent),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]),
    )
    return inner


def _status_chip(text: str, ok: bool) -> Paragraph:
    bg = "#E0EDE5" if ok else "#F6E4D2"
    fg = "#3D7C57" if ok else "#C9772A"
    return Paragraph(
        f"<para alignment='center'><font size=8 color='{fg}' "
        f"backColor='{bg}'>&nbsp;&nbsp;{text}&nbsp;&nbsp;</font></para>",
        _BODY,
    )


# Paragraph styles are built lazily once getSampleStyleSheet() is called inside
# generate_pdf; we expose _BODY at module scope after that so helpers can use it.
_BODY: ParagraphStyle | None = None


def generate_pdf(state: SessionState) -> str:
    global _BODY
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = (state.name or "client").strip().lower().replace(" ", "_")
    path = os.path.join(OUTPUT_DIR, f"plan_{safe_name}_{time.strftime('%Y%m%d_%H%M%S')}.pdf")
    client_label = state.name or "Client"

    sheet = getSampleStyleSheet()
    body = ParagraphStyle("body", parent=sheet["BodyText"], fontName="Helvetica",
                          fontSize=9.5, leading=13.5, textColor=INK)
    caption = ParagraphStyle("caption", parent=body, fontSize=8.5, leading=12,
                             textColor=INK_SOFT)
    caption_italic = ParagraphStyle("caption_italic", parent=caption,
                                    fontName="Helvetica-Oblique")
    h1 = ParagraphStyle("h1", parent=sheet["Title"], fontName="Times-Bold",
                        fontSize=20, leading=24, textColor=NAVY, spaceAfter=2)
    h2 = ParagraphStyle("h2", parent=sheet["Heading2"], fontName="Times-Bold",
                        fontSize=14, leading=17, textColor=NAVY, spaceAfter=0)
    h3 = ParagraphStyle("h3", parent=sheet["Heading3"], fontName="Times-Bold",
                        fontSize=11.5, leading=14, textColor=NAVY, spaceAfter=0)
    eyebrow = ParagraphStyle("eyebrow", parent=body, fontSize=7.5, leading=10,
                             textColor=CHAMPAGNE, fontName="Helvetica-Bold")
    _BODY = body
    styles = {"body": body, "caption": caption, "h1": h1, "h2": h2, "h3": h3,
              "eyebrow": eyebrow, "caption_italic": caption_italic}

    # Common table conventions: no heavy grid; navy header row; alternating cream stripes.
    def _premium_table_style(num_cols: int) -> TableStyle:
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), IVORY),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8.5),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TEXTCOLOR", (0, 1), (-1, -1), INK),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CREAM]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, CHAMPAGNE),
            ("LINEABOVE", (0, 1), (-1, 1), 0.0, colors.white),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, HAIRLINE),
        ])

    story: list = [NextPageTemplate("later")]

    # --- Cover spacer: leave room for the navy band drawn by _draw_cover_band ---
    story.append(Spacer(1, COVER_BAND_H - 18 * mm))

    # --- Hero KPI cards ---
    r = state.ratios or {}
    surplus = r.get("surplus")
    savings_rate = r.get("savings_rate")
    savings_band = (r.get("savings_band") or "—").title()
    risk_label = (state.risk_profile or "—").title()
    surplus_accent = GREEN if (surplus or 0) > 0 else AMBER
    savings_accent = GREEN if (savings_rate or 0) >= 0.30 else AMBER
    kpi_row = Table(
        [[
            _kpi_card("Monthly surplus", _inr(surplus), surplus_accent),
            _kpi_card("Savings rate", f"{(savings_rate or 0) * 100:.0f}%", savings_accent),
            _kpi_card("Risk profile", risk_label, CHAMPAGNE),
        ]],
        colWidths=[58 * mm, 58 * mm, 58 * mm],
        style=TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]),
    )
    story.append(kpi_row)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        f"Savings band: <b>{savings_band}</b>  &nbsp;•&nbsp;  "
        f"Debt-to-income: <b>{(r.get('debt_to_income') or 0) * 100:.0f}%</b> "
        f"({(r.get('dti_band') or '—').title()})", caption))

    # --- Financial Snapshot table (clean two-column) ---
    story.extend(_section_heading("Financial Snapshot", styles))
    snapshot_rows = [
        ["Monthly income", _inr(state.monthly_income)],
        ["Monthly non-EMI expenses", _inr(state.monthly_expenses)],
        ["Monthly EMI", _inr(state.monthly_emi or 0)],
        ["Monthly surplus", _inr(surplus)],
        ["Savings rate",
         f"{(savings_rate or 0) * 100:.0f}%  ({savings_band})"],
        ["Debt-to-income",
         f"{(r.get('debt_to_income') or 0) * 100:.0f}%  ({(r.get('dti_band') or '—').title()})"],
        ["Risk profile", risk_label],
    ]
    snapshot = Table(snapshot_rows, colWidths=[65 * mm, 109 * mm])
    snapshot.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("TEXTCOLOR", (0, 0), (0, -1), INK_SOFT),
        ("TEXTCOLOR", (1, 0), (1, -1), INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, HAIRLINE),
        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
    ]))
    story.append(snapshot)

    # --- Expense breakdown ---
    if state.expense_breakdown:
        story.extend(_section_heading("Expense Breakdown", styles))
        story.append(Paragraph("3-month average from your account aggregator pull.", caption))
        story.append(Spacer(1, 2 * mm))
        rows = [["Category", "Monthly average"]]
        for key, value in state.expense_breakdown.items():
            rows.append([key.replace("_", " ").title(), _inr(value)])
        tbl = Table(rows, colWidths=[110 * mm, 64 * mm], style=_premium_table_style(2))
        story.append(tbl)

    # --- Existing Portfolio ---
    if state.portfolio:
        p = state.portfolio
        story.extend(_section_heading("Existing Portfolio", styles))
        rows = [["Fund", "Type", "Value", "Monthly SIP", "Rating"]]
        flagged_idxs: list[int] = []
        for i, h in enumerate(p["holdings"]):
            flagged = bool(h.get("flag"))
            name = h["fund"]
            if flagged:
                flagged_idxs.append(i + 1)
            rows.append([
                name,
                h["type"].title(),
                _inr(h["current_value"]),
                _inr(h["monthly_sip"]),
                f"{h['rating']}/5",
            ])
        rows.append(["Total", "", _inr(p["total_value"]),
                     _inr(p["total_monthly_sip"]), ""])
        style = _premium_table_style(5)
        # Override the alternating-row pattern for flagged rows with amber tint
        # and bold the totals line.
        last_row = len(rows) - 1
        style.add("FONTNAME", (0, last_row), (-1, last_row), "Helvetica-Bold")
        style.add("BACKGROUND", (0, last_row), (-1, last_row), CREAM_DEEP)
        style.add("LINEABOVE", (0, last_row), (-1, last_row), 0.6, NAVY_EDGE)
        for idx in flagged_idxs:
            style.add("BACKGROUND", (0, idx), (-1, idx), AMBER_SOFT)
            style.add("TEXTCOLOR", (0, idx), (0, idx), AMBER)
        story.append(Table(rows,
                           colWidths=[66 * mm, 22 * mm, 30 * mm, 30 * mm, 26 * mm],
                           style=style))

        if p.get("review_methodology"):
            story.append(Spacer(1, 2 * mm))
            story.append(Paragraph(p["review_methodology"], caption))
        if p.get("underperformers"):
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph(
                f"<font color='#C9772A'><b>Flagged underperformers:</b></font> "
                f"{', '.join(p['underperformers'])}.", body))
            for review in p.get("fund_reviews", []):
                if review.get("status") != "good":
                    story.append(Paragraph(
                        f"<b>{review['fund']}</b> &mdash; {review['reason']}.", caption))

    # --- Your Goals ---
    story.append(PageBreak())
    story.extend(_section_heading("Your Goals", styles))
    rows = [["#", "Goal", "Today", "Future", "Existing covers", "Monthly SIP", "Status"]]
    for g in sorted(state.goals, key=lambda g: g.priority):
        coverage = "—"
        if g.projected_from_existing is not None and g.inflated_target:
            pct = g.projected_from_existing / g.inflated_target * 100
            coverage = f"{_inr(g.projected_from_existing)}  ({pct:.0f}%)"
        rows.append([
            str(g.priority),
            f"{g.name}  ({g.horizon_years}y)",
            _inr(g.target_amount_today),
            _inr(g.inflated_target),
            coverage,
            _inr(g.required_sip),
            _status_chip("FUNDED" if g.funded else "PARKED", g.funded),
        ])
    goals_style = _premium_table_style(7)
    goals_style.add("ALIGN", (0, 0), (0, -1), "CENTER")
    goals_style.add("ALIGN", (2, 1), (5, -1), "RIGHT")
    story.append(Table(rows,
                       colWidths=[8 * mm, 50 * mm, 22 * mm, 24 * mm, 34 * mm, 22 * mm, 20 * mm],
                       style=goals_style))

    # --- Recommended Portfolio (Phased by Goal) ---
    story.extend(_section_heading("Recommended Portfolio", styles))
    if state.proposed_portfolios:
        total_sip = sum(pp["monthly_sip"] for pp in state.proposed_portfolios.values())
        story.append(Paragraph(
            f"Total monthly investment across funded goals: <b>{_inr(total_sip)}</b>.",
            body))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph(
            "Each goal is phased by horizon: short-term runs one debt-heavy phase, "
            "medium-term runs two phases (balanced → debt), long-term runs three "
            "phases (equity-heavy → balanced → debt glide-down).", caption))
        story.append(Spacer(1, 4 * mm))

        for pp in state.proposed_portfolios.values():
            current = pp.get("current_phase") or pp["phases"][0]
            a = current["allocation"]
            equity, debt, gold = a["equity"], a["debt"], a["gold"]

            goal_block: list = []
            chip_text = f"&nbsp;{pp['horizon_bucket'].upper()}-TERM  •  {pp['horizon_years']}Y&nbsp;"
            header_row = Table(
                [[
                    Paragraph(f"<font name='Times-Bold' size=12 color='#0A1628'>"
                              f"{pp['goal']}</font>", body),
                    Paragraph(
                        f"<para alignment='right'><font name='Helvetica-Bold' size=7.5 "
                        f"color='#0A1628' backColor='#E1C589'>{chip_text}</font></para>",
                        body),
                ]],
                colWidths=[110 * mm, 64 * mm],
                style=TableStyle([
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]),
            )
            goal_block.append(header_row)
            goal_block.append(Paragraph(
                f"Monthly SIP <b>{_inr(pp['monthly_sip'])}</b>  &nbsp;•&nbsp;  "
                f"Current phase <b>P{current['phase']}</b> for {current['duration_years']}y",
                caption))
            goal_block.append(Spacer(1, 2 * mm))

            # Allocation bar + legend
            goal_block.append(_AllocationBar(equity, debt, gold, width=174 * mm))
            legend = (
                f"<font color='#0A1628'>■</font> Equity {equity * 100:.0f}%  &nbsp;&nbsp;"
                f"<font color='#5D6478'>■</font> Debt {debt * 100:.0f}%  &nbsp;&nbsp;"
                f"<font color='#C9A961'>■</font> Gold {gold * 100:.0f}%"
            )
            goal_block.append(Spacer(1, 1.5 * mm))
            goal_block.append(Paragraph(legend, caption))
            goal_block.append(Spacer(1, 3 * mm))

            fund_rows = [["Fund", "Category", "Monthly SIP"]]
            for f in current["funds"]:
                fund_rows.append([
                    f["fund"],
                    f.get("category", f.get("type", "")).title()
                    if isinstance(f.get("category", f.get("type", "")), str) else "",
                    _inr(f["monthly_sip"]),
                ])
            fund_style = _premium_table_style(3)
            fund_style.add("ALIGN", (2, 1), (2, -1), "RIGHT")
            goal_block.append(Table(fund_rows,
                                    colWidths=[100 * mm, 44 * mm, 30 * mm],
                                    style=fund_style))

            if len(pp["phases"]) > 1:
                future = "  ›  ".join(
                    f"P{ph['phase']} ({ph['duration_years']}y)" for ph in pp["phases"][1:])
                goal_block.append(Spacer(1, 1.5 * mm))
                goal_block.append(Paragraph(
                    f"<font color='#5D6478'>Future glide path:</font> {future}",
                    caption))

            if pp.get("selection_basis"):
                goal_block.append(Spacer(1, 1 * mm))
                goal_block.append(Paragraph(pp["selection_basis"], caption_italic))

            goal_block.append(Spacer(1, 6 * mm))
            story.append(KeepTogether(goal_block))
    else:
        story.append(Paragraph("To be finalized with your advisor.", body))

    # --- Action Plan ---
    story.extend(_section_heading("Action Plan", styles))
    actions: list[str] = []
    if state.portfolio and state.portfolio.get("underperformers"):
        actions.append(
            f"Switch out of underperformers: <b>"
            f"{', '.join(state.portfolio['underperformers'])}</b>.")
    if state.proposed_portfolios:
        total_sip = sum(pp["monthly_sip"] for pp in state.proposed_portfolios.values())
        actions.append(
            f"Start the new monthly SIP of <b>{_inr(total_sip)}</b> across the "
            f"per-goal current-phase portfolios above. Each goal glides between "
            f"phases as it approaches.")
    parked = [g.name for g in state.goals if not g.funded]
    if parked:
        actions.append(
            f"Revisit parked goal(s) &mdash; <b>{', '.join(parked)}</b> &mdash; "
            f"when income grows.")
    actions.append("Review this plan every 12 months or after any major life event.")

    action_rows = []
    for i, a in enumerate(actions, 1):
        badge = Paragraph(
            f"<para alignment='center'><font name='Times-Bold' size=11 color='#0A1628'>"
            f"{i}</font></para>", body)
        action_rows.append([badge, Paragraph(a, body)])
    action_table = Table(action_rows, colWidths=[10 * mm, 164 * mm])
    action_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), CREAM),
        ("LINEAFTER", (0, 0), (0, -1), 1.6, CHAMPAGNE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, CREAM]),
    ]))
    story.append(action_table)

    # --- Disclaimer ---
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=0.3, color=HAIRLINE))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(
        "<font size=7 color='#9AA0AE'>Generated by Wealth Expert (demo). "
        "Assumed long-run returns: equity 11%, debt 7%. Mutual fund investments "
        "are subject to market risks; past performance is not indicative of "
        "future returns. This document is for illustration only and is not "
        "investment advice.</font>", body))

    # --- Build document with per-page chrome ---
    def on_first_page(canvas: Canvas, _doc) -> None:
        _draw_cover_band(canvas, state)
        _draw_footer(canvas, canvas.getPageNumber(), client_label)

    def on_later_pages(canvas: Canvas, _doc) -> None:
        _draw_header_band(canvas)
        _draw_footer(canvas, canvas.getPageNumber(), client_label)

    doc = BaseDocTemplate(
        path,
        pagesize=A4,
        leftMargin=SIDE_MARGIN,
        rightMargin=SIDE_MARGIN,
        topMargin=COVER_BAND_H + 4 * mm,
        bottomMargin=20 * mm,
        title="Your Financial Plan",
        author="Wealth Expert",
    )
    first_frame = Frame(
        SIDE_MARGIN, 18 * mm,
        PAGE_W - 2 * SIDE_MARGIN,
        PAGE_H - COVER_BAND_H - 22 * mm,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="first",
    )
    later_frame = Frame(
        SIDE_MARGIN, 18 * mm,
        PAGE_W - 2 * SIDE_MARGIN,
        PAGE_H - HEADER_BAND_H - 24 * mm,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        id="later",
    )
    doc.addPageTemplates([
        PageTemplate(id="first", frames=[first_frame], onPage=on_first_page),
        PageTemplate(id="later", frames=[later_frame], onPage=on_later_pages),
    ])
    doc.build(story)
    return path
