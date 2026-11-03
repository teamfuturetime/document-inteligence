"""Build the VT-042 submission from committed source and measured evidence."""

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from xml.sax.saxutils import escape

import fitz
from PIL import Image as PILImage
from PIL import ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    KeepInFrame,
    Paragraph,
    Preformatted,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parents[2]
TASK = ROOT / "homework/VT-042"
EVIDENCE = TASK / "evidence"
REPO = "https://github.com/teamfuturetime/document-inteligence"
BRANCH = "codex/bt3-vt042-async-retry"
BASELINE = "db727496312087af6495aa12e7c9a52df3dfa230"
RED = "9a76a6ed5d064336df5ba3eb275f7ee9996e5615"
FIX = "6289d84e3da04690472506f07c3107549db92181"
W, H = A4
MARGIN = 43
WIDTH = W - 2 * MARGIN


def load(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output/pdf/BT3_23001920_VT-042.pdf")
    parser.add_argument("--font-dir", type=Path, default=Path("C:/Windows/Fonts"))
    args = parser.parse_args()
    for name, file in (("TNR", "times.ttf"), ("TNRB", "timesbd.ttf")):
        pdfmetrics.registerFont(TTFont(name, str(args.font_dir / file)))
    styles = {
        "body": ParagraphStyle("body", fontName="TNR", fontSize=12, leading=14.8, spaceAfter=7),
        "small": ParagraphStyle("small", fontName="TNR", fontSize=10, leading=12, spaceAfter=6),
        "h1": ParagraphStyle("h1", fontName="TNRB", fontSize=17, leading=20, spaceAfter=12),
        "h2": ParagraphStyle(
            "h2",
            fontName="TNRB",
            fontSize=12.5,
            leading=15,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "title": ParagraphStyle("title", fontName="TNRB", fontSize=22, leading=26, spaceAfter=9),
        "code": ParagraphStyle("code", fontName="TNR", fontSize=9.4, leading=11, spaceAfter=7),
    }

    def clean(value):
        return str(value).replace("–", "-").replace("—", "-").replace("\u2011", "-")

    def p(text, style="body", *, raw=False):
        return Paragraph(clean(text) if raw else escape(clean(text)), styles[style])

    def h2(text):
        return p(text, "h2")

    def code(text):
        return Preformatted(clean(text), styles["code"])

    def link(label, url):
        return p(f'<link href="{url}"><u>{escape(label)}</u></link>', "small", raw=True)

    def table(headers, rows, widths, size=9.6):
        normal = ParagraphStyle("cell", fontName="TNR", fontSize=size, leading=size + 1.8)
        bold = ParagraphStyle("head", parent=normal, fontName="TNRB")
        data = [[Paragraph(escape(clean(value)), bold) for value in headers]]
        data += [
            [Paragraph(escape(clean(value)).replace("\n", "<br/>"), normal) for value in row]
            for row in rows
        ]
        result = Table(data, colWidths=[WIDTH * width for width in widths], hAlign="LEFT")
        result.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LINEABOVE", (0, 0), (-1, 0), 0.7, "black"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.7, "black"),
                    ("LINEBELOW", (0, -1), (-1, -1), 0.7, "black"),
                    ("LINEBELOW", (0, 1), (-1, -2), 0.25, "#aaaaaa"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return result

    pages = []
    audit = load("remote-audit.json")["branches"]
    performance = load("performance.json")
    pairwise = load("pairwise.json")
    coverage = load("coverage-summary.json")
    repeat = load("repeat.json")
    browser = load("browser-e2e.json")
    from report_pages import compose

    pages, reflection = compose(
        SimpleNamespace(p=p, h2=h2, table=table, code=code, link=link),
        SimpleNamespace(
            audit=audit,
            performance=performance,
            pairwise=pairwise,
            coverage=coverage,
            repeat=repeat,
            browser=browser,
            repo=REPO,
            branch=BRANCH,
            baseline=BASELINE,
            red=RED,
            fix=FIX,
            root=ROOT,
            evidence=EVIDENCE,
        ),
    )
    assert 250 <= len(reflection.split()) <= 350
    assert len(pages) == 11
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = ROOT / "runtime/vt042/pdf-qa"
    temporary.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(args.output), pagesize=A4)
    document.setTitle("BT3_23001920_VT-042 - Phạm Nhật Quang")
    document.setAuthor("Phạm Nhật Quang")
    scales = []
    for number, items in enumerate(pages, 1):
        document.setFont("TNR", 9)
        document.drawString(MARGIN, H - 25, "BÀI TẬP CÁ NHÂN 3 | SE2026-T11 | AI-02 | VT-042")
        document.setLineWidth(0.45)
        document.line(MARGIN, H - 31, W - MARGIN, H - 31)
        frame = KeepInFrame(WIDTH, H - 91, items, mode="shrink", hAlign="LEFT", vAlign="TOP")
        _, height = frame.wrapOn(document, WIDTH, H - 91)
        frame.drawOn(document, MARGIN, H - 43 - height)
        scales.append(getattr(frame, "_scale", 1))
        document.line(MARGIN, 35, W - MARGIN, 35)
        document.setFont("TNR", 9)
        document.drawString(MARGIN, 22, "Phạm Nhật Quang | 23001920")
        label = f"{number}/8" if number <= 8 else f"Phụ lục {number - 8}/3"
        document.drawRightString(W - MARGIN, 22, label)
        document.showPage()
    document.save()
    doc = fitz.open(args.output)
    thumbs = []
    for index, page in enumerate(doc):
        image = page.get_pixmap(matrix=fitz.Matrix(1.3, 1.3), alpha=False)
        image.save(temporary / f"page-{index + 1:02}.png")
        thumb = PILImage.frombytes("RGB", (image.width, image.height), image.samples)
        thumb.thumbnail((298, 421))
        tile = PILImage.new("RGB", (318, 452), "white")
        tile.paste(thumb, ((318 - thumb.width) // 2, 18))
        ImageDraw.Draw(tile).text((10, 433), str(index + 1), fill="black")
        thumbs.append(tile)
    sheet = PILImage.new("RGB", (954, 1808), "#dddddd")
    for index, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((index % 3) * 318, (index // 3) * 452))
    sheet.save(temporary / "contact-sheet.png")
    (temporary / "layout.json").write_text(
        json.dumps(
            {
                "main_pages": 8,
                "appendix_pages": 3,
                "reflection_words": len(reflection.split()),
                "scales": scales,
                "pdf_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(args.output)
    print(
        "Pages:",
        len(doc),
        "reflection words:",
        len(reflection.split()),
        "scales:",
        scales,
    )


if __name__ == "__main__":
    main()
