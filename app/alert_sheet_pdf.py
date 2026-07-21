"""Server-side PDF rendering for the validated SAVE-US alert-sheet contract."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .alert_sheet_contract import validate_alert_sheet


NAVY = colors.HexColor("#003F70")
BLUE = colors.HexColor("#1284BD")
ORANGE = colors.HexColor("#FF6A00")
INK = colors.HexColor("#0B2740")
MUTED = colors.HexColor("#506176")
SKY = colors.HexColor("#E8F5FF")
SAFETY = colors.HexColor("#FFF4E9")


def render_alert_sheet_pdf(
    sheet: dict,
    *,
    generated_at: datetime | None = None,
    logo_path: str | Path | None = None,
    public_image_path: str | Path | None = None,
) -> bytes:
    """Render one A4 PDF from a validated, public-safe alert-sheet payload."""
    sheet = validate_alert_sheet(sheet)
    generated_at = _normalise_datetime(generated_at or datetime.now(timezone.utc))
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=17 * mm,
        rightMargin=17 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"SAVE-US alert sheet - {sheet['title']}",
        author="SAVE-US CEMAC Emergency Network",
    )
    styles = _styles()
    story = []

    brand_cells = []
    if logo_path and Path(logo_path).is_file():
        logo = Image(str(logo_path), width=18 * mm, height=18 * mm, kind="proportional")
        brand_cells.append(logo)
    brand_cells.append(Paragraph("<b>SAVE-US</b><br/><font size=7>CEMAC EMERGENCY NETWORK</font>", styles["brand"]))
    header = Table([[brand_cells, Paragraph("PUBLISHED", styles["status"])]], colWidths=[132 * mm, 40 * mm])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 2.5, ORANGE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("ALIGN", (-1, 0), (-1, 0), "RIGHT"),
    ]))
    story.extend([header, Spacer(1, 11 * mm)])

    story.append(Paragraph(_escape(sheet["category_label"]).upper(), styles["category"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(_escape(sheet["title"]), styles["title"]))
    story.append(Spacer(1, 4 * mm))
    if sheet["public_media"] and public_image_path and Path(public_image_path).is_file():
        # This path is a server-created JPEG derivative, never the original upload.
        image = Image(str(public_image_path), width=120 * mm, height=92 * mm, kind="proportional")
        image.hAlign = "CENTER"
        story.extend([image, Spacer(1, 5 * mm)])
    story.append(Paragraph(_escape(sheet["summary"]), styles["summary"]))
    story.append(Spacer(1, 7 * mm))

    metadata = [
        ("APPROXIMATE AREA", sheet["approximate_location"]),
        ("COVERAGE", sheet["coverage"]),
        ("PUBLISHED", sheet["published_label"]),
    ]
    if sheet["expires_label"]:
        metadata.append(("ALERT EXPIRY", sheet["expires_label"]))
    story.append(_metadata_table(metadata, styles))
    story.append(Spacer(1, 7 * mm))
    story.append(_safety_box(sheet["safety_guidance"], styles))
    story.append(Spacer(1, 14 * mm))

    footer = Table(
        [[Paragraph(f"<b>{_escape(sheet['source'])}</b>", styles["footer"]), Paragraph(
            f"Generated {_escape(generated_at.strftime('%d %b %Y · %H:%M UTC'))}", styles["footer-right"]
        )]],
        colWidths=[88 * mm, 84 * mm],
    )
    footer.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor("#CBDDEA")),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(footer)
    document.build(story)
    return buffer.getvalue()


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("SaveUsBrand", parent=base["Normal"], textColor=NAVY, fontName="Helvetica", fontSize=15, leading=17),
        "status": ParagraphStyle("SaveUsStatus", parent=base["Normal"], textColor=colors.HexColor("#17642A"), fontName="Helvetica-Bold", fontSize=8, leading=10, alignment=TA_LEFT),
        "category": ParagraphStyle("SaveUsCategory", parent=base["Normal"], textColor=BLUE, fontName="Helvetica-Bold", fontSize=8, leading=10, spaceAfter=0),
        "title": ParagraphStyle("SaveUsTitle", parent=base["Heading1"], textColor=NAVY, fontName="Helvetica-Bold", fontSize=25, leading=29, spaceAfter=0),
        "summary": ParagraphStyle("SaveUsSummary", parent=base["BodyText"], textColor=INK, fontName="Helvetica", fontSize=12, leading=18, leftIndent=5 * mm, borderColor=BLUE, borderWidth=2.5, borderPadding=0),
        "meta-label": ParagraphStyle("SaveUsMetaLabel", parent=base["Normal"], textColor=MUTED, fontName="Helvetica-Bold", fontSize=6.5, leading=8),
        "meta-value": ParagraphStyle("SaveUsMetaValue", parent=base["Normal"], textColor=NAVY, fontName="Helvetica-Bold", fontSize=9, leading=12),
        "safety-label": ParagraphStyle("SaveUsSafetyLabel", parent=base["Normal"], textColor=colors.HexColor("#934000"), fontName="Helvetica-Bold", fontSize=8, leading=10),
        "safety": ParagraphStyle("SaveUsSafety", parent=base["BodyText"], textColor=INK, fontName="Helvetica", fontSize=9.5, leading=14),
        "footer": ParagraphStyle("SaveUsFooter", parent=base["Normal"], textColor=NAVY, fontName="Helvetica-Bold", fontSize=7.5, leading=9),
        "footer-right": ParagraphStyle("SaveUsFooterRight", parent=base["Normal"], textColor=MUTED, fontName="Helvetica", fontSize=7.5, leading=9, alignment=2),
    }


def _metadata_table(items: list[tuple[str, str]], styles: dict[str, ParagraphStyle]) -> Table:
    cells = [
        Paragraph(f"{_escape(label)}<br/><br/>{_escape(value)}", styles["meta-value"])
        for label, value in items
    ]
    # A two-column grid stays balanced for the optional road-alert expiry cell.
    rows = [cells[index:index + 2] for index in range(0, len(cells), 2)]
    if len(rows[-1]) == 1:
        rows[-1].append("")
    table = Table(rows, colWidths=[86 * mm, 86 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SKY),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E7F3")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D5E7F3")),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return table


def _safety_box(guidance: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[Paragraph("SAFETY GUIDANCE", styles["safety-label"])], [Paragraph(_escape(guidance), styles["safety"])]],
        colWidths=[172 * mm],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SAFETY),
        ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#F3C28B")),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def _escape(value: str) -> str:
    return escape(value).replace("\n", "<br/>")


def _normalise_datetime(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


__all__ = ["render_alert_sheet_pdf"]
