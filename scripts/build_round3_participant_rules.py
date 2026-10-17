"""Build the participant-facing Round 3 rules poster and quick guide."""

from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf"
PDF = OUT / "Round3_Participant_Rules_Poster.pdf"

INK = colors.HexColor("#120C0E")
PANEL = colors.HexColor("#241317")
PANEL_2 = colors.HexColor("#311A20")
PEACH = colors.HexColor("#FFB599")
PINK = colors.HexColor("#FF4F87")
CREAM = colors.HexColor("#FFF6EF")
MUTED = colors.HexColor("#C8AFA8")
LINE = colors.HexColor("#6C3944")


def register_fonts() -> tuple[str, str]:
    regular = "Helvetica"
    bold = "Helvetica-Bold"
    candidates = [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (Path("C:/Windows/Fonts/calibri.ttf"), Path("C:/Windows/Fonts/calibrib.ttf")),
    ]
    for normal, strong in candidates:
        if normal.exists() and strong.exists():
            pdfmetrics.registerFont(TTFont("RulesRegular", str(normal)))
            pdfmetrics.registerFont(TTFont("RulesBold", str(strong)))
            return "RulesRegular", "RulesBold"
    return regular, bold


REGULAR, BOLD = register_fonts()


def paragraph(c: canvas.Canvas, text: str, x: float, y: float, w: float, size: float = 10,
              color=CREAM, bold: bool = False, leading: float | None = None,
              align: int = TA_LEFT) -> float:
    style = ParagraphStyle(
        "rules",
        fontName=BOLD if bold else REGULAR,
        fontSize=size,
        leading=leading or size * 1.28,
        textColor=color,
        alignment=align,
        spaceAfter=0,
    )
    p = Paragraph(text, style)
    _pw, ph = p.wrap(w, 100 * mm)
    p.drawOn(c, x, y - ph)
    return ph


def background(c: canvas.Canvas, page: int, label: str) -> None:
    width, height = A4
    c.setFillColor(INK)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#3E1D24"))
    c.circle(width + 8 * mm, height - 18 * mm, 52 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#2B131B"))
    c.circle(-14 * mm, 22 * mm, 48 * mm, fill=1, stroke=0)
    c.setStrokeColor(LINE)
    c.setLineWidth(0.7)
    c.line(16 * mm, 14 * mm, width - 16 * mm, 14 * mm)
    c.setFillColor(MUTED)
    c.setFont(REGULAR, 7.5)
    c.drawString(16 * mm, 8.5 * mm, "ASYMPTOTES BMSIT · ROUND 03 · PARTICIPANT GUIDE")
    c.drawRightString(width - 16 * mm, 8.5 * mm, f"{label} · {page:02d}/02")


def badge(c: canvas.Canvas, text: str, x: float, y: float, w: float) -> None:
    c.setFillColor(PINK)
    c.roundRect(x, y, w, 8 * mm, 4 * mm, fill=1, stroke=0)
    c.setFillColor(CREAM)
    c.setFont(BOLD, 8)
    c.drawCentredString(x + w / 2, y + 2.55 * mm, text)


def card(c: canvas.Canvas, number: str, title: str, body: str, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(PANEL)
    c.setStrokeColor(LINE)
    c.roundRect(x, y, w, h, 4 * mm, fill=1, stroke=1)
    c.setFillColor(PEACH)
    c.circle(x + 9 * mm, y + h - 10 * mm, 4.6 * mm, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont(BOLD, 8)
    c.drawCentredString(x + 9 * mm, y + h - 12.5 * mm, number)
    paragraph(c, title, x + 17 * mm, y + h - 5.7 * mm, w - 23 * mm, 11.5, CREAM, True)
    paragraph(c, body, x + 7 * mm, y + h - 21 * mm, w - 14 * mm, 8.6, MUTED, False, 11.2)


def page_one(c: canvas.Canvas) -> None:
    width, height = A4
    background(c, 1, "HOW IT WORKS")
    badge(c, "30 MINUTES · 13 TEAMS · AUCTION + PUZZLE FLOOR", 18 * mm, height - 25 * mm, 98 * mm)
    paragraph(c, "THE UNDERGROUND<br/><font color='#FF4F87'>EXCHANGE.</font>", 18 * mm,
              height - 36 * mm, 174 * mm, 35, CREAM, True, 34)
    paragraph(c, "Three devices. Eight puzzle stations. One live clue auction.<br/>Choose your moves carefully—every point can change the final field.",
              19 * mm, height - 112 * mm, 168 * mm, 11, MUTED, False, 15)

    gap = 5 * mm
    cw = (174 * mm - gap) / 2
    ch = 37 * mm
    left = 18 * mm
    right = left + cw + gap
    top = height - 165 * mm
    card(c, "1", "Use up to 3 logins", "Your team may keep a maximum of three active devices. Use them for puzzle runs, the auction, or a mix of both.", left, top, cw, ch)
    card(c, "2", "Choose the player", "Before a run, select the member who will play. That choice controls the personal table cooldown.", right, top, cw, ch)
    card(c, "3", "Receive a table", "The system assigns an available station. Go only to that table and keep your team screen ready.", left, top - ch - gap, cw, ch)
    card(c, "4", "Send the 3-digit code", "Press Send code when you reach the laptop. The same code appears only on your device and that station screen.", right, top - ch - gap, cw, ch)
    card(c, "5", "Solve in 75 seconds", "The station starts after identity confirmation. Enter one final answer before time ends. Correct earns that table's points; wrong or timeout earns zero.", left, top - 2 * (ch + gap), cw, ch)
    card(c, "6", "Bid while you play", "Clue tokens can appear at any time. Winning bids are deducted from your balance, so spend only when the information is worth it.", right, top - 2 * (ch + gap), cw, ch)

    c.setFillColor(PEACH)
    c.roundRect(18 * mm, 20 * mm, 174 * mm, 20 * mm, 5 * mm, fill=1, stroke=0)
    paragraph(c, "MORE SOLVED RUNS = MORE POINTS  ·  SMARTER BIDS = MORE OPTIONS", 23 * mm, 34.2 * mm,
              164 * mm, 10.5, INK, True, 12, TA_CENTER)


def page_two(c: canvas.Canvas) -> None:
    width, height = A4
    background(c, 2, "RULES & FAIR PLAY")
    badge(c, "READ BEFORE ROUND 3 OPENS", 18 * mm, height - 25 * mm, 65 * mm)
    paragraph(c, "PLAY FAST.<br/><font color='#FF4F87'>PLAY FAIR.</font>", 18 * mm, height - 37 * mm,
              174 * mm, 28, CREAM, True, 29)

    rules = [
        ("DEVICE LIMIT", "Only three active team sessions are allowed. Closing a tab may take a short time to release the slot; always use Log out when switching devices."),
        ("ONE PLAYER, ONE RUN", "Select the real player before requesting a table. Show the team screen to the station admin. Do not share or guess access codes."),
        ("TABLE COOLDOWN", "A team cannot immediately repeat its last completed table. A player may return to the same table only after completing two other station runs—win or loss."),
        ("QUESTION IS FINAL", "Once a station assigns a question, it is consumed and will never be used again. Cancelling or missing the reservation does not restore it."),
        ("ANSWER WINDOW", "You receive 75 seconds after the admin confirms the code. Submit carefully: spelling, format and accepted alternatives are checked by the system."),
        ("POINTS", "Correct station answers add the displayed reward. Wrong answers and timeouts add zero. Auction wins deduct the final bid. Your team alone can view its balance and history."),
        ("AUCTION", "Bids must be within your available balance. A bid is serious and cannot be withdrawn. Only the winning team receives that clue token after the lot closes."),
        ("ROUND 4 GATE", "The super admin will announce the number of teams advancing. Final balance determines the provisional field; a tie at the cutoff is resolved before results are locked. Preserve the secret code collected across earlier rounds."),
    ]
    c.setFillColor(PINK)
    c.roundRect(18 * mm, height - 105 * mm, 174 * mm, 18 * mm, 5 * mm, fill=1, stroke=0)
    paragraph(c, "If a laptop, timer or network fails: stop, keep the screen visible, and call an organiser. Do not refresh repeatedly or start another run until the issue is recorded.",
              24 * mm, height - 91.5 * mm, 162 * mm, 8.6, CREAM, True, 10.6, TA_CENTER)

    y = height - 119 * mm
    for index, (title, body) in enumerate(rules, start=1):
        c.setFillColor(PANEL_2 if index % 2 == 0 else PANEL)
        c.roundRect(18 * mm, y - 17 * mm, 174 * mm, 15.5 * mm, 3 * mm, fill=1, stroke=0)
        c.setFillColor(PEACH)
        c.setFont(BOLD, 7.7)
        c.drawString(23 * mm, y - 7.5 * mm, f"{index:02d}  {title}")
        paragraph(c, body, 66 * mm, y - 3.4 * mm, 119 * mm, 7.65, MUTED, False, 9.2)
        y -= 18.3 * mm


def build() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(PDF), pagesize=A4)
    c.setTitle("Round 3 Participant Rules — The Underground Exchange")
    c.setAuthor("Club Asymptotes, BMSIT")
    page_one(c)
    c.showPage()
    page_two(c)
    c.save()
    assert len(PdfReader(str(PDF)).pages) == 2
    return PDF


if __name__ == "__main__":
    output = build()
    print(f"Built {output} ({len(PdfReader(str(output)).pages)} pages)")
