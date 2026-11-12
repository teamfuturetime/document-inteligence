"""Export five assignment requirements across eight main pages plus appendices.

Optional dependency: reportlab. Usage: python build_report.py source.md out.pdf
Font paths default to macOS Arial; override VT044_FONT_DIR for another system.
"""
import html
import os
from pathlib import Path
import re
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Preformatted,
)


fonts = Path(os.environ.get("VT044_FONT_DIR", "/System/Library/Fonts/Supplemental"))
pdfmetrics.registerFont(TTFont("Body", str(fonts / "Arial.ttf")))
pdfmetrics.registerFont(TTFont("Body-Bold", str(fonts / "Arial Bold.ttf")))
pdfmetrics.registerFont(TTFont("Body-Italic", str(fonts / "Arial Italic.ttf")))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")

BODY = ParagraphStyle("body", fontName="Body", fontSize=9, leading=12.2,
                      spaceAfter=6, splitLongWords=True, alignment=TA_LEFT)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.2, leading=9.3, spaceAfter=0)
HEAD = ParagraphStyle("head", parent=BODY, fontName="Body-Bold", fontSize=13,
                      leading=17, spaceAfter=11, textColor=colors.HexColor("#183650"))
TITLE = ParagraphStyle("title", parent=HEAD, fontSize=17, leading=22)
SUBHEAD = ParagraphStyle("subhead", parent=BODY, fontName="Body-Bold", fontSize=10,
                         leading=13, spaceBefore=5, spaceAfter=5,
                         textColor=colors.HexColor("#183650"))
CODE = ParagraphStyle("code", parent=BODY, fontSize=7.4, leading=10,
                      leftIndent=7, backColor=colors.HexColor("#f3f6f8"), spaceAfter=7)


def inline(text):
    text = html.escape(text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" color="#17648a">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font color="#34475a">\1</font>', text)
    return text


def blocks(section, width):
    lines = section.strip().splitlines()
    result = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith("```"):
            index += 1
            code = []
            while index < len(lines) and not lines[index].startswith("```"):
                code.append(lines[index])
                index += 1
            # Wrap exceptionally long commands instead of clipping the page.
            wrapped = []
            for value in code:
                while pdfmetrics.stringWidth(value, "Body", 7.4) > width - 18:
                    cut = len(value)
                    while pdfmetrics.stringWidth(value[:cut], "Body", 7.4) > width - 18:
                        cut -= 1
                    wrapped.append(value[:cut])
                    value = "    " + value[cut:]
                wrapped.append(value)
            result.extend([Preformatted("\n".join(wrapped), CODE), Spacer(1, 4)])
            index += 1
            continue
        if line.startswith("|"):
            rows = []
            while index < len(lines) and lines[index].startswith("|"):
                values = [item.strip() for item in lines[index].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", value) for value in values):
                    rows.append(values)
                index += 1
            count = len(rows[0])
            if count == 6:
                fractions = [.055, .095, .105, .285, .39, .07]
            elif count == 5:
                fractions = [.12, .29, .20, .13, .26]
            elif count == 4:
                fractions = [.17, .31, .29, .23]
            elif count == 2:
                fractions = [.09, .91]
            else:
                fractions = [.23, .34, .43]
            cell_rows = [[Paragraph(inline(value), CELL) for value in row] for row in rows]
            table = Table(cell_rows, colWidths=[width * part for part in fractions], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6eff5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafb")]),
                ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#b7c8d3")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            result.extend([table, Spacer(1, 8)])
            continue
        if line.startswith("# "):
            result.append(Paragraph(inline(line[2:]), TITLE))
            index += 1
            continue
        if line.startswith("## "):
            result.append(Paragraph(inline(line[3:]), HEAD))
            index += 1
            continue
        if line.startswith("### "):
            result.append(Paragraph(inline(line[4:]), SUBHEAD))
            index += 1
            continue
        paragraph = []
        while index < len(lines) and lines[index].strip() and not lines[index].startswith(("|", "#", "```")):
            item = lines[index]
            hard_break = item.endswith("  ")
            paragraph.append(inline(item.strip()) + ("<br/>" if hard_break else " "))
            index += 1
            if re.match(r"^(?:- |\d+\. )", item):
                break
        result.append(Paragraph("".join(paragraph), BODY))
    return result


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#b7c8d3"))
    canvas.line(42, 37, A4[0] - 42, 37)
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(colors.HexColor("#536b7c"))
    canvas.drawString(42, 25, "Nguyễn Công Trí | 23001945 | AI-02 / VT-044")
    canvas.drawRightString(A4[0] - 42, 25, f"{doc.page}")
    canvas.restoreState()


def main():
    source, destination = map(Path, sys.argv[1:3])
    destination.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(str(destination), pagesize=A4, rightMargin=42,
                                 leftMargin=42, topMargin=36, bottomMargin=49,
                                 title="BT3 - 23001945 - VT-044", author="Nguyễn Công Trí")
    story = []
    sections = source.read_text().split("<!-- PAGEBREAK -->")
    for index, section in enumerate(sections):
        if index:
            story.append(PageBreak())
        story.extend(blocks(section, A4[0] - 84))
    document.build(story, onFirstPage=footer, onLaterPages=footer)
    print(destination)


if __name__ == "__main__":
    main()
