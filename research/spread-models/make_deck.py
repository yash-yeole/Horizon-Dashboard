"""Build the <=10 slide deck (output/Brent_Spread_Distribution.pptx) with python-pptx."""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

HERE = os.path.dirname(__file__)
FIGD = os.path.join(HERE, "output", "figs")
OUT = os.path.join(HERE, "output", "Brent_Spread_Distribution.pptx")

# palette
NAVY = RGBColor.from_string("1E2761")
NAVY2 = RGBColor.from_string("2A3570")
AMBER = RGBColor.from_string("E8A33D")
RED = RGBColor.from_string("C0392B")
TEAL = RGBColor.from_string("1C7293")
ICE = RGBColor.from_string("CADCFC")
WHITE = RGBColor.from_string("FFFFFF")
DARK = RGBColor.from_string("1A1A2E")
MUTE = RGBColor.from_string("6B7280")
LIGHT = RGBColor.from_string("F4F6FB")

HEAD = "Georgia"
BODY = "Calibri"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
SW, SH = 13.333, 7.5
BLANK = prs.slide_layouts[6]


def slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    r.fill.solid(); r.fill.fore_color.rgb = bg; r.line.fill.background()
    r.shadow.inherit = False
    s.shapes._spTree.remove(r._element); s.shapes._spTree.insert(2, r._element)
    return s


def rect(s, x, y, w, h, color, line=None, lw=1.0):
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    r.fill.solid(); r.fill.fore_color.rgb = color
    r.shadow.inherit = False
    if line is None:
        r.line.fill.background()
    else:
        r.line.color.rgb = line; r.line.width = Pt(lw)
    return r


def txt(s, x, y, w, h, runs, size=14, color=DARK, bold=False, font=BODY,
        align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False, sp_after=4, line=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    if isinstance(runs, str):
        runs = [(runs, {})]
    first = True
    for line_runs in runs:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align; p.space_after = Pt(sp_after)
        if line is not None:
            p.line_spacing = line
        if isinstance(line_runs, tuple):
            line_runs = [line_runs]
        for text, o in line_runs:
            r = p.add_run(); r.text = text
            r.font.name = o.get("font", font); r.font.size = Pt(o.get("size", size))
            r.font.bold = o.get("bold", bold); r.font.italic = o.get("italic", italic)
            r.font.color.rgb = o.get("color", color)
    return tb


def pic(s, path, x, y, maxw, maxh, align="center", valign="top"):
    iw, ih = Image.open(path).size
    ar = iw / ih
    w, h = maxw, maxw / ar
    if h > maxh:
        h, w = maxh, maxh * ar
    px = x + (maxw - w) / 2 if align == "center" else x
    py = y + (maxh - h) / 2 if valign == "center" else y
    s.shapes.add_picture(path, Inches(px), Inches(py), Inches(w), Inches(h))


def header(s, kicker, title, dark=False):
    c = WHITE if dark else NAVY
    rect(s, 0.6, 0.5, 0.12, 0.5, AMBER)
    txt(s, 0.85, 0.46, 11.8, 0.3, kicker.upper(), size=12, color=AMBER, bold=True, font=BODY)
    txt(s, 0.85, 0.74, 11.8, 0.7, title, size=27, color=c, bold=True, font=HEAD)


def fig(name):
    return os.path.join(FIGD, name)


# ---- Slide 1: title ---------------------------------------------------------
s = slide(NAVY)
rect(s, 0, 0, SW, 0.18, AMBER)
txt(s, 0.9, 1.5, 11.5, 0.4, "QUANTITATIVE FRAMEWORK", size=14, color=AMBER, bold=True)
txt(s, 0.9, 2.0, 11.6, 1.6,
    [[("From News Event to Brent ", {}), ("Calendar-Spread Distribution", {"color": AMBER})]],
    size=40, color=WHITE, bold=True, font=HEAD)
txt(s, 0.9, 3.5, 11.2, 1.0,
    [[("“Israel launches strikes on Iranian energy infrastructure. Iran threatens "
       "closure of the Strait of Hormuz.”", {"italic": True})]],
    size=18, color=ICE)
txt(s, 0.9, 4.7, 11.5, 0.5,
    "Probability distributions for M1–M2, M2–M4, M1–M6 over a 1-week horizon",
    size=16, color=WHITE)
rect(s, 0.9, 5.7, 5.2, 0.02, NAVY2)
txt(s, 0.9, 5.85, 11.5, 0.5,
    [[("Scenario-mixture model · 5yr ICE Brent (1-min) event study · news-severity scoring",
       {"color": MUTE, "size": 13})]])

# ---- Slide 2: approach ------------------------------------------------------
s = slide(WHITE)
header(s, "Approach", "A news event shifts a distribution, not a single number")
txt(s, 0.85, 1.7, 11.6, 0.7,
    [[("The deliverable is the ", {}), ("shape of uncertainty", {"bold": True, "color": NAVY}),
      (". We model each spread’s 1-week change as a probability-weighted mixture of three "
       "regimes, each calibrated to real analogs in 5 years of minute-level Brent data.", {})]],
    size=15, color=DARK)
steps = [
    ("1", "SCORE THE NEWS", "A severity scorecard turns the headline into the three regime "
     "probabilities — reproducible for any future event.", TEAL),
    ("2", "CALIBRATE MAGNITUDE", "An event study sets each regime’s drift and tail from "
     "history (Russia-22, Gaza-23, Iran–Israel ’24/’25).", AMBER),
    ("3", "SIMULATE", "400k-draw Monte Carlo of the mixture → EV, 50% / 90% ranges, with "
     "parameter-uncertainty CIs and a backtest.", RED),
]
x = 0.85
for num, t, body, col in steps:
    w = 3.7
    rect(s, x, 2.55, w, 3.4, LIGHT)
    rect(s, x, 2.55, w, 0.12, col)
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.3), Inches(2.9), Inches(0.7), Inches(0.7))
    c.fill.solid(); c.fill.fore_color.rgb = col; c.line.fill.background(); c.shadow.inherit = False
    tf = c.text_frame; tf.word_wrap = False
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = num; r.font.bold = True; r.font.size = Pt(26)
    r.font.color.rgb = WHITE; r.font.name = HEAD
    txt(s, x + 0.3, 3.85, w - 0.6, 0.5, t, size=16, color=NAVY, bold=True, font=HEAD)
    txt(s, x + 0.3, 4.4, w - 0.6, 1.4, body, size=13, color=DARK, line=1.05)
    x += w + 0.28
txt(s, 0.85, 6.25, 11.6, 0.6,
    [[("Why a mixture? ", {"bold": True, "color": NAVY}),
      ("Geopolitical weeks are fat-tailed and skewed — a single Gaussian understates the "
       "Hormuz tail. The mixture makes scenarios and their probabilities explicit.", {})]],
    size=13, color=MUTE)

# ---- Slide 3: scoring -------------------------------------------------------
s = slide(WHITE)
header(s, "Creativity · Step 1", "News-severity scoring → scenario probabilities")
pic(s, fig("03_scoring.png"), 0.6, 1.7, 8.1, 4.7, align="center", valign="center")
bx = 9.0
txt(s, bx, 1.75, 3.9, 0.4, "DERIVED PROBABILITIES", size=12, color=MUTE, bold=True)
yy = 2.15
for name, p, col in [("Escalation / Hormuz", "22%", RED),
                     ("Contained risk-premium", "50%", AMBER),
                     ("De-escalation / fizzle", "28%", TEAL)]:
    rect(s, bx, yy, 3.85, 0.95, LIGHT); rect(s, bx, yy, 0.1, 0.95, col)
    txt(s, bx + 0.25, yy + 0.06, 2.4, 0.8, name, size=14, color=NAVY, bold=True,
        anchor=MSO_ANCHOR.MIDDLE)
    txt(s, bx + 2.3, yy + 0.02, 1.45, 0.9, p, size=30, color=col, bold=True, font=HEAD,
        align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    yy += 1.1
txt(s, bx, yy + 0.05, 3.9, 1.3,
    [[("Composite severity ", {}), ("S = 0.68", {"bold": True, "color": NAVY}),
      (", mapped via p", {}), ("esc", {"size": 9}), ("=0.05+0.37S² (convex tail) and a "
      "fizzle floor honouring the empirical mean-reversion base rate.", {})]],
    size=12, color=MUTE, line=1.05)

# ---- Slide 4: event study ---------------------------------------------------
s = slide(WHITE)
header(s, "Analytical rigor · Step 2", "Event study: how shock weeks actually priced")
pic(s, fig("02_eventstudy.png"), 0.6, 1.7, 8.3, 4.9, align="center", valign="center")
bx = 9.1
pts = [("Russia 2022", "Only realised supply shock → escalation/Hormuz template (+9.5 on M1–M6).", RED),
       ("Iran–Israel ’24/’25", "Direct exchanges → moderate risk-premium build. Base case.", AMBER),
       ("Hamas / Apr-24", "No oil-supply hit → premium priced then faded. Fizzle.", TEAL)]
yy = 1.85
for t, b, col in pts:
    rect(s, bx, yy, 3.8, 1.45, LIGHT); rect(s, bx, yy, 0.1, 1.45, col)
    txt(s, bx + 0.25, yy + 0.12, 3.4, 0.4, t, size=15, color=NAVY, bold=True, font=HEAD)
    txt(s, bx + 0.25, yy + 0.55, 3.4, 0.85, b, size=12.5, color=DARK, line=1.03)
    yy += 1.6
txt(s, bx, yy + 0.02, 3.8, 0.6,
    [[("Five events → three clean regimes.", {"bold": True, "color": NAVY})]],
    size=13, color=NAVY)

# ---- Slide 5: mixture calibration ------------------------------------------
s = slide(WHITE)
header(s, "Statistical thinking · Step 3", "The scenario mixture, calibrated")
rows = [
    ["Regime", "Distribution", "M1–M2", "M2–M4", "M1–M6", "Prob"],
    ["Escalation / Hormuz", "Lognormal (right-skew)", "+2.3", "+5.0", "+10.7", "22%"],
    ["Contained / premium", "Normal", "+0.5", "+0.6", "+1.6", "50%"],
    ["De-escalation / fizzle", "Normal", "−0.2", "−0.2", "−0.6", "28%"],
]
tbl = s.shapes.add_table(4, 6, Inches(0.85), Inches(1.85), Inches(7.4), Inches(2.5)).table
tbl.columns[0].width = Inches(1.9); tbl.columns[1].width = Inches(2.0)
for c in range(2, 5):
    tbl.columns[c].width = Inches(0.9)
tbl.columns[5].width = Inches(0.8)
for ci, val in enumerate(rows[0]):
    cell = tbl.cell(0, ci); cell.fill.solid(); cell.fill.fore_color.rgb = NAVY
    p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER if ci else PP_ALIGN.LEFT
    r = p.add_run(); r.text = val; r.font.bold = True; r.font.size = Pt(12.5)
    r.font.color.rgb = WHITE; r.font.name = BODY
    cell.vertical_anchor = MSO_ANCHOR.MIDDLE
cols = [RED, AMBER, TEAL]
for ri in range(1, 4):
    for ci, val in enumerate(rows[ri]):
        cell = tbl.cell(ri, ci); cell.fill.solid()
        cell.fill.fore_color.rgb = LIGHT if ri % 2 else WHITE
        p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER if ci else PP_ALIGN.LEFT
        r = p.add_run(); r.text = val; r.font.size = Pt(12.5); r.font.name = BODY
        r.font.color.rgb = DARK
        if ci == 0:
            r.font.bold = True; r.font.color.rgb = cols[ri - 1]
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
txt(s, 0.85, 4.7, 7.4, 2.2, [
    [("Escalation as a lognormal", {"bold": True, "color": NAVY}),
     (" — median anchored to the Russia-2022 impulse; 95th pct ≈ 2× median for a "
      "genuine Hormuz interruption (in barrels, far larger than Russia). A symmetric Normal "
      "cannot represent that tail.", {})],
    [("Contained & fizzle as Normals", {"bold": True, "color": NAVY}),
     (" around their event-cluster means; widths from the unconditional weekly vol.", {})],
], size=13.5, color=DARK, line=1.12, sp_after=8)
rect(s, 8.55, 1.95, 4.45, 3.95, LIGHT)
txt(s, 8.8, 2.15, 4.0, 0.4, "MIXTURE → SIMULATED SHAPE", size=11, color=MUTE, bold=True)
pic(s, fig("04_distributions.png"), 8.65, 2.55, 4.25, 2.9, align="center", valign="center")
txt(s, 8.8, 5.0, 4.0, 0.8,
    [[("Right-skew + fat tail is the escalation regime. Full-size on the next slide.",
       {"italic": True})]], size=12, color=MUTE, line=1.05)

# ---- Slide 6: RESULTS -------------------------------------------------------
s = slide(NAVY)
rect(s, 0.6, 0.5, 0.12, 0.5, AMBER)
txt(s, 0.85, 0.46, 11.8, 0.3, "THE DELIVERABLE", size=12, color=AMBER, bold=True)
txt(s, 0.85, 0.74, 11.8, 0.7, "1-week spread-change distribution", size=27, color=WHITE,
    bold=True, font=HEAD)
data = [
    ("M1–M2", "+0.70", "[−0.14, +1.29]", "[−0.80, +2.99]", "69%"),
    ("M2–M4", "+1.34", "[−0.15, +1.80]", "[−0.92, +6.43]", "70%"),
    ("M1–M6", "+2.97", "[−0.29, +4.23]", "[−2.09, +13.7]", "71%"),
]
heads = ["Spread", "Expected value", "50% range", "90% range", "P(widen)"]
colx = [0.85, 3.0, 5.5, 8.4, 11.4]
colw = [2.0, 2.4, 2.8, 2.9, 1.6]
ytop = 1.9
for i, (hh, xx, ww) in enumerate(zip(heads, colx, colw)):
    txt(s, xx, ytop, ww, 0.4, hh.upper(), size=12, color=AMBER, bold=True)
yy = 2.5
for row in data:
    rect(s, 0.85, yy, 12.1, 0.02, NAVY2)
    for i, (val, xx, ww) in enumerate(zip(row, colx, colw)):
        col = WHITE; sz = 16; bold = False
        if i == 0:
            col = AMBER; sz = 22; bold = True
        if i == 1:
            sz = 22; bold = True
        txt(s, xx, yy + 0.18, ww, 0.7, val, size=sz, color=col, bold=bold,
            font=HEAD if i in (0, 1) else BODY, anchor=MSO_ANCHOR.MIDDLE)
    yy += 1.05
rect(s, 0.85, yy, 12.1, 0.02, NAVY2)
txt(s, 0.85, yy + 0.25, 12.1, 1.0, [
    [("Read: ", {"bold": True, "color": AMBER}),
     ("modal outcome is a moderate backwardation build; a fat right tail opens if Hormuz is "
      "genuinely threatened (M1–M6 P95 ≈ +13.7), and ~28% chance the move fades. "
      "Convention: positive = backwardation (near minus far).", {"color": ICE})]],
    size=14, line=1.1)

# ---- Slide 7: distributions + fan ------------------------------------------
s = slide(WHITE)
header(s, "Visualising the distribution", "Skew, tails, and the curve fan")
pic(s, fig("04_distributions.png"), 0.6, 1.75, 7.2, 3.6, align="center", valign="center")
pic(s, fig("05_fan.png"), 8.0, 1.75, 5.0, 3.6, align="center", valign="center")
txt(s, 0.85, 5.55, 11.6, 1.5, [
    [("Front vs back. ", {"bold": True, "color": NAVY}),
     ("M1–M2 (front) is most information-sensitive per dollar — a supply scare lands "
      "on the prompt, so it moves first and reverts fastest. M2–M4 (belly) is muted: the "
      "market prices a temporary disruption. M1–M6 captures the whole steepening — "
      "largest absolute move and fattest tail.", {})]],
    size=13.5, color=DARK, line=1.12)

# ---- Slide 8: robustness ----------------------------------------------------
s = slide(WHITE)
header(s, "Analytical & statistical rigor", "Does the model hold up? Uncertainty + backtest")
txt(s, 0.85, 1.7, 6.0, 0.4, "PARAMETER UNCERTAINTY (90% CI on the statistic)", size=12,
    color=MUTE, bold=True)
purows = [["Spread", "EV 90% CI", "P95 90% CI"],
          ["M1–M2", "[+0.36, +1.09]", "[+1.6, +4.7]"],
          ["M2–M4", "[+0.62, +2.17]", "[+2.6, +10.0]"],
          ["M1–M6", "[+1.49, +4.90]", "[+6.2, +21.3]"]]
t = s.shapes.add_table(4, 3, Inches(0.85), Inches(2.1), Inches(5.9), Inches(2.0)).table
for ci in range(3):
    t.columns[ci].width = Inches([1.7, 2.1, 2.1][ci])
for ri, row in enumerate(purows):
    for ci, val in enumerate(row):
        cell = t.cell(ri, ci); cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY if ri == 0 else (LIGHT if ri % 2 else WHITE)
        p = cell.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.CENTER if ci else PP_ALIGN.LEFT
        r = p.add_run(); r.text = val; r.font.size = Pt(12.5); r.font.name = BODY
        r.font.bold = (ri == 0 or ci == 0)
        r.font.color.rgb = WHITE if ri == 0 else (NAVY if ci == 0 else DARK)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
txt(s, 0.85, 4.35, 6.0, 2.6, [
    [("Small-N honesty.", {"bold": True, "color": NAVY})],
    [("With only 5 events the regime means are themselves uncertain. We sample means from "
      "their standard errors and weights from a Dirichlet around the scored probabilities — "
      "error bars on the error bars.", {})],
], size=13.5, color=DARK, line=1.12, sp_after=8)
txt(s, 7.1, 1.7, 6.0, 0.4, "BACKTEST: model percentile of each realised move", size=12,
    color=MUTE, bold=True)
pic(s, fig("06_backtest.png"), 7.0, 2.1, 6.1, 3.6, align="center", valign="top")
txt(s, 7.1, 5.75, 6.0, 1.2, [
    [("Well-calibrated: ", {"bold": True, "color": NAVY}),
     ("fizzle events land at the ~20–25th model percentile, the direct Israel–Iran "
      "analogs at ~50th, and the Russia supply shock at ~88th — the model brackets history.", {})]],
    size=12.5, color=DARK, line=1.1)

# ---- Slide 9: sensitivity + anchor nuance ----------------------------------
s = slide(WHITE)
header(s, "Market understanding", "Sensitivity & the asymmetry that matters")
pic(s, fig("07_sensitivity.png"), 0.6, 1.75, 8.2, 3.3, align="center", valign="center")
txt(s, 0.85, 5.2, 8.1, 1.8, [
    [("Bounded downside, open upside. ", {"bold": True, "color": NAVY}),
     ("As p(escalation) varies, the P05 floor barely moves — the fizzle regime caps the "
      "downside — while the upper tail fans out. That asymmetry is exactly what a "
      "single-number forecast would miss.", {})]],
    size=13.5, color=DARK, line=1.12)
rect(s, 9.1, 1.75, 3.75, 5.0, LIGHT); rect(s, 9.1, 1.75, 3.75, 0.12, AMBER)
txt(s, 9.35, 2.0, 3.3, 0.5, "Nuance: the anchor", size=16, color=NAVY, bold=True, font=HEAD)
txt(s, 9.35, 2.6, 3.3, 4.0, [
    [("We anchor on the ", {}), ("pre-event", {"bold": True}),
     (" level, so “fizzle” is only mildly negative (‘sell-the-fact’ + soft "
      "fundamentals, e.g. Apr-24).", {})],
    [("If the news has ", {}), ("already", {"bold": True}),
     (" gapped the curve up, de-escalation unwinds the whole premium → a ", {}),
     ("much larger", {"bold": True, "color": RED}), (" drop.", {})],
    [("Both framings ship; pre-event is the conservative default.", {"italic": True, "color": MUTE})],
], size=12.5, color=DARK, line=1.1, sp_after=8)

# ---- Slide 10: conclusions --------------------------------------------------
s = slide(NAVY)
rect(s, 0, 0, SW, 0.18, AMBER)
rect(s, 0.6, 0.6, 0.12, 0.5, AMBER)
txt(s, 0.85, 0.56, 11.8, 0.3, "TAKEAWAYS", size=12, color=AMBER, bold=True)
txt(s, 0.85, 0.85, 11.8, 0.7, "News → curve, quantified", size=28, color=WHITE,
    bold=True, font=HEAD)
items = [
    ("A reusable pipeline", "Score any headline → probabilities; event study → magnitude; "
     "mixture → full distribution. Not a point forecast."),
    ("Base case + fat tail", "Moderate backwardation build (50%), with a 22% Hormuz tail that "
     "dominates the 90% range, especially M1–M6."),
    ("Term-structure logic", "Front spikes and reverts fastest; belly muted; M1–M6 carries "
     "the steepening and the tail."),
    ("Honest about uncertainty", "Right-skewed tail, parameter-uncertainty CIs, and a backtest "
     "that brackets every historical event."),
]
yy = 2.0
for t, b in items:
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.9), Inches(yy + 0.05), Inches(0.22), Inches(0.22))
    c.fill.solid(); c.fill.fore_color.rgb = AMBER; c.line.fill.background(); c.shadow.inherit = False
    txt(s, 1.35, yy, 11.4, 0.5, [[(t + "  ", {"bold": True, "color": AMBER, "size": 17}),
                                  (b, {"color": ICE, "size": 14})]], font=HEAD, line=1.05)
    yy += 1.12
txt(s, 0.85, 6.95, 11.8, 0.4,
    "Code: research/spread-models/  ·  scoring.py · event_study.py · mixture_model.py · "
    "news_to_spread_distribution.ipynb", size=11, color=MUTE)

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides._sldIdLst))
