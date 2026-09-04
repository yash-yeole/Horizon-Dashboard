"""Build the <=10 slide STRUCTURAL deck -> output/Brent_Spread_Structural.pptx (python-pptx)."""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

HERE = os.path.dirname(__file__)
FIGD = os.path.join(HERE, "output", "figs")
OUT = os.path.join(HERE, "output", "Brent_Spread_Structural.pptx")

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


def simple_table(s, rows, x, y, widths, fontsize=12.5, head_bg=NAVY, accent_col0=None):
    nr, nc = len(rows), len(rows[0])
    t = s.shapes.add_table(nr, nc, Inches(x), Inches(y),
                           Inches(sum(widths)), Inches(0.5 * nr)).table
    for ci, wd in enumerate(widths):
        t.columns[ci].width = Inches(wd)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci); cell.fill.solid()
            cell.fill.fore_color.rgb = head_bg if ri == 0 else (LIGHT if ri % 2 else WHITE)
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if ci == 0 else PP_ALIGN.CENTER
            r = p.add_run(); r.text = val; r.font.size = Pt(fontsize); r.font.name = BODY
            r.font.bold = (ri == 0 or ci == 0)
            if ri == 0:
                r.font.color.rgb = WHITE
            elif ci == 0 and accent_col0 is not None:
                r.font.color.rgb = accent_col0[ri - 1]
            else:
                r.font.color.rgb = DARK
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
    return t


# ============================================================ Slide 1: title
s = slide(NAVY)
rect(s, 0, 0, SW, 0.18, AMBER)
txt(s, 0.9, 1.35, 11.5, 0.4, "STRUCTURAL DRIVER MODEL", size=14, color=AMBER, bold=True)
txt(s, 0.9, 1.85, 11.6, 1.6,
    [[("From Fundamentals to a Brent ", {}), ("Calendar-Spread Distribution", {"color": AMBER})]],
    size=38, color=WHITE, bold=True, font=HEAD)
txt(s, 0.9, 3.35, 11.4, 1.0,
    [[("“Israel launches strikes on Iranian energy infrastructure. Iran threatens "
       "closure of the Strait of Hormuz.”", {"italic": True})]],
    size=18, color=ICE)
txt(s, 0.9, 4.5, 11.5, 0.5,
    "Probability distributions for M1–M2, M2–M4, M1–M6 over a 1-week horizon",
    size=16, color=WHITE)
rect(s, 0.9, 5.5, 5.2, 0.02, NAVY2)
txt(s, 0.9, 5.65, 11.7, 0.8,
    [[("Supply-at-risk · buffer accessibility · persistence · geopolitical premium  "
       "→  calibrated curve response  →  400k Monte Carlo", {"color": MUTE, "size": 13})]])

# ============================================================ Slide 2: approach
s = slide(WHITE)
header(s, "Approach", "Fundamentals drive the curve — not a single number")
txt(s, 0.85, 1.65, 11.8, 0.8,
    [[("We translate the headline into ", {}), ("fundamental drivers", {"bold": True, "color": NAVY}),
      (", push them through a response function ", {}),
      ("calibrated to reproduce history", {"bold": True, "color": NAVY}),
      (", then Monte-Carlo over scenarios and drivers to get the full 1-week distribution.", {})]],
    size=15, color=DARK, line=1.1)
steps = [
    ("1", "SCORE THE NEWS", "A severity scorecard turns the headline into probabilities "
     "across five physical scenarios — reproducible for any event.", TEAL),
    ("2", "DRIVERS → CURVE", "supply, buffer×access, persistence, premium → effective "
     "shortfall E → the front impulse and the curve fan.", AMBER),
    ("3", "SIMULATE", "400k-draw Monte Carlo over scenarios and the driver ranges within "
     "each → EV, 50% / 90% ranges, tornado.", RED),
]
x = 0.85
for num, t, body, col in steps:
    w = 3.78
    rect(s, x, 2.65, w, 2.5, LIGHT)
    rect(s, x, 2.65, w, 0.12, col)
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.3), Inches(2.95), Inches(0.65), Inches(0.65))
    c.fill.solid(); c.fill.fore_color.rgb = col; c.line.fill.background(); c.shadow.inherit = False
    tf = c.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = num; r.font.bold = True; r.font.size = Pt(24)
    r.font.color.rgb = WHITE; r.font.name = HEAD
    txt(s, x + 0.3, 3.75, w - 0.6, 0.5, t, size=15, color=NAVY, bold=True, font=HEAD)
    txt(s, x + 0.3, 4.25, w - 0.55, 1.0, body, size=12.5, color=DARK, line=1.05)
    x += w + 0.26
# the response-function one-liner
rect(s, 0.85, 5.45, 11.62, 1.45, NAVY)
txt(s, 1.1, 5.6, 11.2, 0.4, "THE ENGINE, IN ONE LINE", size=11, color=AMBER, bold=True)
txt(s, 1.1, 5.95, 11.2, 0.9, [
    [("coverage = min(buffer×access / supply, 1)      "
      "E = supply×location×(1 − κ·coverage)      "
      "ΔM1–M2 = β·E + premium", {"font": "Consolas", "size": 13, "color": WHITE})],
    [("M2–M4 = (a₂₄ + b₂₄·ρ)·ΔM1–M2        "
      "M1–M6 = (a₁₆ + b₁₆·ρ)·ΔM1–M2        "
      "— deferred months fan out with persistence ρ", {"font": "Consolas", "size": 13, "color": ICE})],
], line=1.25)

# ============================================================ Slide 3: event study
s = slide(WHITE)
header(s, "Empirical anchors", "Five years of Brent: how shock weeks actually priced")
pic(s, fig("struct_02_eventstudy.png"), 0.6, 1.7, 8.3, 4.9, align="center", valign="center")
bx = 9.1
pts = [("Russia 2022", "The only realised supply shock → the escalation template "
        "(+9.5 on M1–M6, deep fan).", RED),
       ("Iran–Israel '24/'25", "Direct exchanges, no supply loss → moderate premium build. "
        "Base case.", AMBER),
       ("Hamas / Apr-24", "No oil-supply hit → premium priced then faded. Fizzle.", TEAL)]
yy = 1.85
for t, b, col in pts:
    rect(s, bx, yy, 3.8, 1.45, LIGHT); rect(s, bx, yy, 0.1, 1.45, col)
    txt(s, bx + 0.25, yy + 0.12, 3.4, 0.4, t, size=15, color=NAVY, bold=True, font=HEAD)
    txt(s, bx + 0.25, yy + 0.55, 3.4, 0.85, b, size=12.5, color=DARK, line=1.03)
    yy += 1.6
txt(s, bx, yy + 0.02, 3.8, 0.7,
    [[("These five events ", {}), ("calibrate the curve response", {"bold": True, "color": NAVY}),
      (" — and later test it.", {})]],
    size=13, color=NAVY)

# ============================================================ Slide 4: scoring -> scenarios
s = slide(WHITE)
header(s, "Step 1 · News → probabilities", "Severity scoring → five physical scenarios")
pic(s, fig("struct_04_scoring.png"), 0.4, 1.75, 8.6, 4.9, align="center", valign="center")
bx = 9.2
txt(s, bx, 1.75, 3.7, 0.4, "DERIVED PROBABILITIES", size=12, color=MUTE, bold=True)
sc_list = [("Rapid de-escalation", "26%", TEAL),
           ("Prolonged containment", "48%", NAVY),
           ("Hormuz harassment", "15%", AMBER),
           ("Iran export infra hit", "6%", RGBColor.from_string("D67D2C")),
           ("Hormuz closure (tail)", "4%", RED)]
yy = 2.2
for name, p, col in sc_list:
    rect(s, bx, yy, 3.7, 0.72, LIGHT); rect(s, bx, yy, 0.1, 0.72, col)
    txt(s, bx + 0.22, yy + 0.04, 2.35, 0.64, name, size=12.5, color=NAVY, bold=True,
        anchor=MSO_ANCHOR.MIDDLE)
    txt(s, bx + 2.6, yy + 0.02, 1.0, 0.68, p, size=22, color=col, bold=True, font=HEAD,
        align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    yy += 0.82
txt(s, bx, yy + 0.05, 3.7, 1.0,
    [[("Composite severity ", {}), ("S = 0.74", {"bold": True, "color": NAVY}),
      (". Scored on 5 factors: supply at risk, directness, duration, buffer adequacy, "
       "escalation dynamics. Stage 2 tilts the escalation family toward the violent tail as S rises.", {})]],
    size=11, color=MUTE, line=1.05)

# ============================================================ Slide 5: Monte Carlo simulation
s = slide(WHITE)
header(s, "Step 2 · Simulation", "400,000 draws: from probabilities to a full distribution")

# --- 4 step cards across the slide ---
steps_mc = [
    (TEAL,   "1",
     "PICK A SCENARIO",
     "Draw one of the 5 scenarios weighted\nby their scored probabilities.",
     ["26%  Rapid de-escalation",
      "48%  Prolonged containment",
      "15%  Hormuz harassment",
      " 6%  Export infra hit",
      " 4%  Hormuz closure (tail)"]),
    (NAVY,   "2",
     "SAMPLE THE DRIVERS",
     "Within that scenario draw each\nphysical driver from its range.",
     ["Supply at risk  ~  triangular(low, mode, high)",
      "Buffer access   ~  triangular(low, mode, high)",
      "Persistence ρ   ~  triangular(low, mode, high)",
      "Geo-premium     ~  triangular(low, mode, high)",
      "OPEC+ buffer    ~  Normal(4.5 mb/d, 0.4)"]),
    (AMBER,  "3",
     "RUN THE RESPONSE FUNCTION",
     "Feed drivers through the structural\nmechanism → three spread moves.",
     ["coverage  =  min(buffer × access / supply, 1)",
      "E         =  supply × (1 − κ · coverage)",
      "ΔM1–M2   =  β · E  +  premium",
      "ΔM2–M4   =  (a₂₄ + b₂₄·ρ) · ΔM1–M2",
      "ΔM1–M6   =  (a₁₆ + b₁₆·ρ) · ΔM1–M2"]),
    (RED,    "4",
     "ADD NOISE & RECORD",
     "Layer calibrated residual noise,\nthen store all three spread moves.",
     ["Noise ~ N(0, 0.45 × weekly vol)",
      "Record ΔM1–M2,  ΔM2–M4,  ΔM1–M6",
      "",
      "Repeat steps 1–4  ×  400,000",
      "→  read empirical quantiles"]),
]

col_w = 3.00
col_gap = 0.11
x0 = 0.55
for i, (col, num, title, desc, bullets) in enumerate(steps_mc):
    cx = x0 + i * (col_w + col_gap)
    rect(s, cx, 1.72, col_w, 4.85, LIGHT)
    rect(s, cx, 1.72, col_w, 0.13, col)   # top colour strip
    # number circle
    circ = s.shapes.add_shape(MSO_SHAPE.OVAL,
                               Inches(cx + col_w/2 - 0.33), Inches(1.92),
                               Inches(0.66), Inches(0.66))
    circ.fill.solid(); circ.fill.fore_color.rgb = col
    circ.line.fill.background(); circ.shadow.inherit = False
    tf = circ.text_frame; p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = num; r.font.bold = True
    r.font.size = Pt(20); r.font.color.rgb = WHITE; r.font.name = HEAD
    # step title
    txt(s, cx + 0.12, 2.70, col_w - 0.22, 0.45, title,
        size=12, color=col, bold=True, font=HEAD, align=PP_ALIGN.CENTER)
    # description
    txt(s, cx + 0.12, 3.18, col_w - 0.22, 0.55, desc,
        size=10.5, color=MUTE, line=1.05, align=PP_ALIGN.CENTER)
    # bullet lines
    bullet_runs = [[(b, {})] for b in bullets]
    txt(s, cx + 0.15, 3.80, col_w - 0.26, 2.55, bullet_runs,
        size=10, color=DARK, line=1.1, sp_after=2)
    # arrow between cards (not after last)
    if i < 3:
        ax = cx + col_w + col_gap/2 - 0.08
        txt(s, ax, 3.4, 0.2, 0.4, "→", size=18, color=AMBER, bold=True,
            align=PP_ALIGN.CENTER)

# bottom output band
rect(s, 0.55, 6.68, 12.22, 0.65, NAVY)
txt(s, 0.75, 6.72, 11.8, 0.55, [
    [("OUTPUT after 400,000 draws:  ", {"bold": True, "color": AMBER}),
     ("EV  ·  50% range [p25, p75]  ·  90% range [p05, p95]  ·  P(spread widens)  ", {"color": WHITE}),
     ("— one distribution per spread, no assumptions about its shape.", {"color": MUTE, "size": 11})]
], size=12.5, line=1.0)

# ============================================================ Slide 6 (was 5): the engine
s = slide(WHITE)
header(s, "Step 2 · The engine", "The response function — two mechanics do the work")
pic(s, fig("struct_03_response.png"), 0.6, 1.75, 12.1, 3.5, align="center", valign="top")
txt(s, 0.85, 5.45, 5.9, 1.6, [
    [("(a) Buffer coverage is non-linear.", {"bold": True, "color": NAVY})],
    [("A 4.5 mb/d buffer fully plugs a small loss but is overwhelmed by a large one — and "
      "in a Hormuz event most spare capacity is ", {}), ("trapped behind the strait", {"bold": True, "color": RED}),
     (", so the effective shortfall E explodes.", {})],
], size=13, color=DARK, line=1.1, sp_after=6)
txt(s, 7.0, 5.45, 5.9, 1.6, [
    [("(b) The curve fans with persistence.", {"bold": True, "color": NAVY})],
    [("A brief premium is front-concentrated (small multiple); a sustained shock drags the "
      "deferred months up too. ", {}), ("ρ separates a 12-day-war spike from a structural re-rating.",
      {"bold": True, "color": NAVY})],
], size=13, color=DARK, line=1.1, sp_after=6)

# ============================================================ Slide 6: scenarios as drivers
s = slide(WHITE)
header(s, "Step 2 · Scenarios", "Each scenario is a distribution over drivers")
rows = [
    ["Scenario", "Supply†", "Access", "ρ", "Premium", "E (mb/d)", "M1–M6"],
    ["Rapid de-escalation", "0.1", "1.0", "0.10", "−0.3", "0.08", "−0.5"],
    ["Prolonged containment", "0.6", "1.0", "0.45", "+0.15", "0.33", "+1.7"],
    ["Hormuz harassment", "2.0", "0.40", "0.50", "+0.30", "1.54", "+7.0"],
    ["Iran export infra hit", "1.8", "0.90", "0.70", "+0.20", "0.92", "+4.9"],
    ["Hormuz closure (tail)", "9.0", "0.25", "0.85", "+0.50", "10.5", "+51.9"],
]
accent = [TEAL, NAVY, AMBER, RGBColor.from_string("D67D2C"), RED]
simple_table(s, rows, 0.85, 1.85, [2.7, 1.1, 1.1, 0.9, 1.25, 1.35, 1.3],
             fontsize=12.5, accent_col0=accent)
txt(s, 0.85, 5.4, 11.7, 0.4,
    [[("† supply-at-risk shown at scenario mode (mb/d); the Monte Carlo samples a "
       "triangular low/mode/high for every driver.", {"italic": True, "color": MUTE})]],
    size=11.5)
txt(s, 0.85, 5.95, 11.7, 1.0, [
    [("The tail is physical, not statistical. ", {"bold": True, "color": NAVY}),
     ("The 3% closure scenario implies an enormous M1–M6 move precisely because access "
      "collapses to 0.25 — coverage → 0, so ~10 mb/d prices through. That is the mechanism a "
      "single lognormal tail hides.", {})]],
    size=13.5, color=DARK, line=1.12)

# ============================================================ Slide 7: RESULTS
s = slide(NAVY)
rect(s, 0.6, 0.5, 0.12, 0.5, AMBER)
txt(s, 0.85, 0.46, 11.8, 0.3, "THE DELIVERABLE", size=12, color=AMBER, bold=True)
txt(s, 0.85, 0.74, 11.8, 0.7, "1-week spread-change distribution", size=27, color=WHITE,
    bold=True, font=HEAD)
data = [
    ("M1–M2", "+1.03", "[+0.07, +1.03]", "[−0.48, +3.20]", "78%"),
    ("M2–M4", "+1.76", "[+0.15, +1.43]", "[−0.46, +4.47]", "81%"),
    ("M1–M6", "+4.10", "[+0.35, +3.54]", "[−1.24, +11.3]", "80%"),
]
heads = ["Spread", "Expected value", "50% range", "90% range", "P(widen)"]
colx = [0.85, 3.0, 5.5, 8.4, 11.4]
colw = [2.0, 2.4, 2.8, 2.9, 1.6]
ytop = 1.95
for hh, xx, ww in zip(heads, colx, colw):
    txt(s, xx, ytop, ww, 0.4, hh.upper(), size=12, color=AMBER, bold=True)
yy = 2.55
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
    yy += 1.0
rect(s, 0.85, yy, 12.1, 0.02, NAVY2)
txt(s, 0.85, yy + 0.22, 12.1, 1.2, [
    [("Read: ", {"bold": True, "color": AMBER}),
     ("modal outcome is a moderate backwardation build (~48% containment weight); a fat right "
      "tail opens if Hormuz access is genuinely threatened (M1–M6 P95 ≈ +11.3, closure tail far "
      "beyond). ~26% chance the move fades. Positive = backwardation (near minus far).", {"color": ICE})]],
    size=14, line=1.12)

# ============================================================ Slide 8: distributions + tornado
s = slide(WHITE)
header(s, "The distribution & what drives it", "Shape of the uncertainty, and its sensitivity")
pic(s, fig("struct_05_distributions.png"), 0.5, 1.65, 7.4, 3.0, align="center", valign="center")
pic(s, fig("struct_08_tornado.png"), 8.0, 1.7, 5.0, 3.0, align="center", valign="center")
txt(s, 0.85, 4.85, 7.1, 2.0, [
    [("Front vs back. ", {"bold": True, "color": NAVY}),
     ("M1–M2 is the raw front impulse — most information-sensitive per dollar. M2–M4 is muted "
      "unless the market believes the disruption is sustained. M1–M6 carries the whole "
      "steepening: largest move, fattest tail.", {})]],
    size=13, color=DARK, line=1.1)
txt(s, 8.05, 4.85, 4.9, 2.0, [
    [("Supply-at-risk dominates. ", {"bold": True, "color": NAVY}),
     ("Then buffer accessibility — ", {}),
     ("where", {"italic": True}),
     (" spare capacity sits matters as much as how much exists. Persistence and premium "
      "fine-tune the fan.", {})]],
    size=13, color=DARK, line=1.1)

# ============================================================ Slide 9: validation (honest)
s = slide(WHITE)
header(s, "Analytical rigor", "Is the curve law remembered — or real?")
pic(s, fig("struct_07_validation.png"), 0.55, 1.7, 5.5, 5.0, align="center", valign="center")
bx = 6.5
txt(s, bx, 1.75, 6.3, 0.9, [
    [("The trap we avoid. ", {"bold": True, "color": RED}),
     ("Simply “reproducing” the five events is in-sample fit — the curve constants were "
      "fit on them, so predicted≈actual by construction. It cannot detect over-fitting.", {})]],
    size=13.5, color=DARK, line=1.12)
txt(s, bx, 3.05, 6.3, 0.9, [
    [("The real test: leave-one-out. ", {"bold": True, "color": NAVY}),
     ("Refit the curve law on 4 events, predict the held-out 5th’s M1–M6 from scratch.", {})]],
    size=13.5, color=DARK, line=1.12)
# headline metric chips
chips = [("LOO curve law", "0.19", TEAL), ("naive baseline", "1.02", MUTE), ("raw spread sd", "4.20", RED)]
cx = bx
for lab, v, col in chips:
    rect(s, cx, 4.0, 1.98, 1.05, LIGHT); rect(s, cx, 4.0, 1.98, 0.1, col)
    txt(s, cx, 4.18, 1.98, 0.5, v, size=26, color=col, bold=True, font=HEAD, align=PP_ALIGN.CENTER)
    txt(s, cx, 4.66, 1.98, 0.35, "RMSE · " + lab, size=10.5, color=MUTE, align=PP_ALIGN.CENTER)
    cx += 2.12
txt(s, bx, 5.3, 6.3, 1.6, [
    [("What this does — and doesn’t — prove.", {"bold": True, "color": NAVY})],
    [("✓ Validated out-of-sample: the curve ", {"color": TEAL}),
     ("geometry", {"bold": True}), (" (5× better than naive).  ", {}),
     ("✗ Not validated: the barrels→price ", {"color": RED}),
     ("magnitude", {"bold": True}),
     (" — we never observe true mb/d-at-risk, so that layer is a transparent prior, not a "
      "fitted claim. n = 5: suggestive, not conclusive.", {})],
], size=12.5, color=DARK, line=1.1, sp_after=6)

# ============================================================ Slide 10: takeaways
s = slide(NAVY)
rect(s, 0, 0, SW, 0.18, AMBER)
rect(s, 0.6, 0.6, 0.12, 0.5, AMBER)
txt(s, 0.85, 0.56, 11.8, 0.3, "TAKEAWAYS", size=12, color=AMBER, bold=True)
txt(s, 0.85, 0.85, 11.8, 0.7, "Fundamentals → curve, quantified", size=28, color=WHITE,
    bold=True, font=HEAD)
items = [
    ("Drivers, not a black box", "Every number traces to a fundamental a trader can argue: "
     "barrels at risk, buffer accessibility, persistence, premium."),
    ("Base case + physical tail", "Moderate backwardation build (48% containment); the fat tail "
     "is four distinct supply outcomes, not one statistical lognormal."),
    ("Honest validation", "Curve geometry holds out-of-sample (LOO RMSE 0.19 vs 4.2 spread); "
     "the magnitude layer is labelled a prior, not over-claimed."),
    ("Term-structure logic", "Front spikes and reverts fastest; belly muted; M1–M6 carries the "
     "steepening and the tail — and is most sensitive to supply-at-risk."),
]
yy = 1.95
for t, b in items:
    c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(0.9), Inches(yy + 0.05), Inches(0.22), Inches(0.22))
    c.fill.solid(); c.fill.fore_color.rgb = AMBER; c.line.fill.background(); c.shadow.inherit = False
    txt(s, 1.35, yy, 11.4, 0.6, [[(t + "  ", {"bold": True, "color": AMBER, "size": 17}),
                                  (b, {"color": ICE, "size": 14})]], font=HEAD, line=1.05)
    yy += 1.18
txt(s, 0.85, 6.95, 11.8, 0.4,
    "Code: research/spread-models/  ·  scoring.py · structural_model.py · gen_figs_structural.py · "
    "structural_spread_model.ipynb", size=11, color=MUTE)

# ============================================================ Slide 11 (Appendix A): MC process + fan
s = slide(WHITE)
header(s, "Appendix A · How the simulation runs", "The Monte Carlo, and the forward curve fan")
# left: the 4-step process
rect(s, 0.85, 1.75, 5.5, 4.9, LIGHT)
txt(s, 1.1, 1.92, 5.0, 0.4, "400,000-DRAW MONTE CARLO", size=12.5, color=NAVY, bold=True, font=HEAD)
mc_steps = [
    ("1  Pick a scenario", "Draw one of the five scenarios with its scored probability "
     "(28 / 50 / 13 / 6 / 3%)."),
    ("2  Sample the drivers", "Within that scenario, draw supply-at-risk, buffer access, "
     "persistence ρ and premium from triangular low/mode/high ranges."),
    ("3  Run the response function", "coverage → effective shortfall E → ΔM1–M2, then fan "
     "out to M2–M4 and M1–M6 via the ρ-multiples."),
    ("4  Add calibrated noise", "Layer residual idiosyncratic noise, record all three "
     "spreads. Repeat 400k×."),
]
yy = 2.45
for t, b in mc_steps:
    txt(s, 1.1, yy, 5.0, 0.4, t, size=13.5, color=AMBER, bold=True, font=HEAD)
    txt(s, 1.1, yy + 0.36, 5.0, 0.7, b, size=12, color=DARK, line=1.05)
    yy += 1.02
# right: the fan chart
txt(s, 6.7, 1.7, 6.2, 0.4, "PROJECTED CURVE FROM TODAY'S LEVELS", size=12, color=MUTE, bold=True)
pic(s, fig("struct_09_fan.png"), 6.6, 2.1, 6.3, 4.4, align="center", valign="top")
txt(s, 6.7, 6.45, 6.2, 0.6,
    [[("Today's curve (M1–M2 3.37, M2–M4 7.15, M1–M6 15.7) plus the simulated 1-week change: "
       "median path with 50% / 90% bands. The fan widens down the curve.", {"italic": True, "color": MUTE})]],
    size=11, line=1.05)

# ============================================================ Slide 12 (Appendix B): sensitivity
s = slide(WHITE)
header(s, "Appendix B · Stress test", "Sensitivity to the escalation probability")
pic(s, fig("struct_10_sensitivity.png"), 0.55, 1.7, 8.2, 4.6, align="center", valign="center")
bx = 9.0
txt(s, bx, 1.8, 3.9, 1.0, [
    [("One assumption, swept. ", {"bold": True, "color": NAVY}),
     ("We hold everything fixed and vary only the total escalation-family weight from "
      "5% to 40% (scored value ≈ 22%), re-running the full Monte Carlo at each.", {})]],
    size=13, color=DARK, line=1.12)
txt(s, bx, 3.25, 3.9, 1.0, [
    [("Bounded downside, open upside. ", {"bold": True, "color": RED}),
     ("The P5 floor barely moves (≈ −1.3) however bullish we get — but the EV and P95 on "
      "M1–M6 climb steeply, from +1.5 to +5.8 EV and to a +36 tail.", {})]],
    size=13, color=DARK, line=1.12)
rect(s, bx, 4.75, 3.9, 1.7, LIGHT); rect(s, bx, 4.75, 0.1, 1.7, AMBER)
txt(s, bx + 0.25, 4.9, 3.5, 1.5, [
    [("Why it matters.", {"bold": True, "color": NAVY})],
    [("The conclusion is robust to the single softest number in the framework: the answer is "
      "directionally the same across the whole plausible range — only the size of the right "
      "tail scales with how much escalation weight you believe.", {})]],
    size=12, color=DARK, line=1.08)

# ============================================================ Slide 13 (Appendix C): backtest
s = slide(WHITE)
header(s, "Appendix C · Distributional backtest", "Does our 1-week distribution bracket real shock weeks?")
pic(s, fig("struct_11_backtest.png"), 0.55, 1.75, 7.7, 4.7, align="center", valign="center")
bx = 8.5
txt(s, bx, 1.8, 4.4, 1.1, [
    [("A second, complementary test. ", {"bold": True, "color": NAVY}),
     ("The leave-one-out test (Slide 9) validates the curve ", {}),
     ("geometry", {"italic": True}),
     (". This asks the distributional question: does the spread of outcomes this model "
      "produces actually contain what real shock weeks delivered?", {})]],
    size=13, color=DARK, line=1.12)
txt(s, bx, 3.35, 4.4, 1.2, [
    [("Read each cell ", {"bold": True, "color": NAVY}),
     ("as the percentile our distribution assigns to that event’s realised 5-day move.", {})]],
    size=13, color=DARK, line=1.12)
rect(s, bx, 4.35, 4.4, 2.15, LIGHT); rect(s, bx, 4.35, 0.1, 2.15, AMBER)
txt(s, bx + 0.25, 4.5, 4.0, 1.95, [
    [("Coherent, not circular.", {"bold": True, "color": NAVY})],
    [("• Calm analogs (Hamas, Apr-24) land in our ", {}),
     ("lower tail (10–16%)", {"bold": True, "color": TEAL}), (".", {})],
    [("• The direct Iran–Israel exchanges sit ", {}),
     ("mid-distribution (~50%)", {"bold": True, "color": AMBER}), (".", {})],
    [("• The one true supply shock, Russia ’22, lands in our ", {}),
     ("upper tail (91–96%)", {"bold": True, "color": RED}), (".", {})],
    [("Every realised move falls inside the range, ordered by severity exactly as the "
      "mechanism predicts.", {"italic": True, "color": MUTE})],
], size=11.5, color=DARK, line=1.06, sp_after=3)

prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides._sldIdLst))
