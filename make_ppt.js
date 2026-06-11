const pptxgen = require("pptxgenjs");
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.title = "HORIZON Energy Terminal";
pres.author = "Yash Yeole";

// ── Palette ───────────────────────────────────────────────────
const BG_DARK   = "0A0F1E";   // slide background
const BG_CARD   = "111827";   // card / panel
const BG_CARD2  = "1E293B";   // lighter card
const TEAL      = "0D9488";   // primary accent
const TEAL_LT   = "5EEAD4";   // light teal
const AMBER     = "F59E0B";   // warning / highlight
const WHITE     = "F8FAFC";   // main text
const MUTED     = "94A3B8";   // secondary text
const BULL      = "10B981";   // bullish green
const BEAR      = "EF4444";   // bearish red
const BORDER    = "1E3A5F";   // border colour

const makeShadow = () => ({ type: "outer", blur: 8, offset: 2, angle: 135, color: "000000", opacity: 0.35 });

// helper: horizontal rule
function hr(slide, y) {
  slide.addShape(pres.shapes.LINE, {
    x: 0.45, y, w: 9.1, h: 0,
    line: { color: BORDER, width: 0.8 }
  });
}

// helper: section chip label
function chip(slide, label, x, y, color = TEAL) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, {
    x, y, w: 1.5, h: 0.28,
    fill: { color }, line: { color }, rectRadius: 0.04
  });
  slide.addText(label.toUpperCase(), {
    x, y, w: 1.5, h: 0.28,
    fontSize: 7.5, bold: true, color: "FFFFFF",
    align: "center", valign: "middle", margin: 0
  });
}

// helper: stat block  (value big, label small below)
function stat(slide, val, label, x, y, valColor = TEAL_LT) {
  slide.addText(val, {
    x, y, w: 2, h: 0.55,
    fontSize: 26, bold: true, color: valColor,
    align: "center", valign: "bottom"
  });
  slide.addText(label, {
    x, y: y + 0.52, w: 2, h: 0.3,
    fontSize: 10, color: MUTED,
    align: "center"
  });
}

// helper: info bullet row
function bullet(slide, icon, text, x, y, w = 4.0) {
  slide.addText(icon, {
    x, y, w: 0.32, h: 0.3,
    fontSize: 12, color: TEAL, bold: true, align: "center"
  });
  slide.addText(text, {
    x: x + 0.3, y, w: w - 0.3, h: 0.3,
    fontSize: 11, color: WHITE
  });
}

// helper: pointer label  "——  text"
function ptr(slide, text, x, y, w = 3.5, color = MUTED) {
  slide.addText("———  " + text, {
    x, y, w, h: 0.28,
    fontSize: 10, color, italic: true
  });
}

// ══════════════════════════════════════════════════════════════
// SLIDE 1 — Title
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };

  // Left accent bar
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0, y: 0, w: 0.08, h: 5.625,
    fill: { color: TEAL }, line: { color: TEAL }
  });

  // Top decorative strip
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.08, y: 0, w: 9.92, h: 0.04,
    fill: { color: TEAL }, line: { color: TEAL }
  });

  // HORIZON wordmark
  s.addText("HORIZON", {
    x: 0.55, y: 1.05, w: 9, h: 1.4,
    fontSize: 88, bold: true, color: WHITE,
    charSpacing: 18, fontFace: "Calibri"
  });

  // Subtitle
  s.addText("ENERGY TERMINAL", {
    x: 0.55, y: 2.35, w: 7, h: 0.5,
    fontSize: 20, color: TEAL_LT, charSpacing: 8, fontFace: "Calibri"
  });

  hr(s, 2.95);

  s.addText(
    "A real-time commodity intelligence platform — live prices, forward curves,\n" +
    "AI-driven news sentiment, statistical anomaly alerts & AIS shipping intelligence.",
    {
      x: 0.55, y: 3.05, w: 7.5, h: 0.9,
      fontSize: 13, color: MUTED, lineSpacingMultiple: 1.4
    }
  );

  // Bottom-right meta
  s.addText("June 2026  ·  Yash Yeole", {
    x: 6.5, y: 5.1, w: 3.3, h: 0.35,
    fontSize: 10, color: MUTED, align: "right"
  });

  // Three teal dots (decorative)
  for (let i = 0; i < 3; i++) {
    s.addShape(pres.shapes.OVAL, {
      x: 8.5 + i * 0.28, y: 1.2, w: 0.16, h: 0.16,
      fill: { color: TEAL }, line: { color: TEAL }
    });
  }
}

// ══════════════════════════════════════════════════════════════
// SLIDE 2 — What is HORIZON?
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });

  s.addText("WHAT IS HORIZON?", {
    x: 0.45, y: 0.3, w: 9, h: 0.55,
    fontSize: 28, bold: true, color: WHITE, charSpacing: 3
  });
  hr(s, 0.92);

  s.addText(
    "HORIZON is an end-to-end energy market intelligence terminal built for commodity traders, analysts, and researchers. It aggregates live market data, news, positioning, inventory, and shipping signals into a single unified interface.",
    {
      x: 0.45, y: 1.05, w: 9.1, h: 0.8,
      fontSize: 13, color: MUTED, lineSpacingMultiple: 1.5
    }
  );

  // 4 value-prop cards
  const cards = [
    { title: "Live Market Data",    body: "Real-time prices for Brent, WTI, RBOB, Heating Oil & Dubai Crude via Yahoo Finance + synthetic proxies.", col: TEAL },
    { title: "AI News Sentiment",   body: "Groq LLM (LLaMA 3.3-70B) scores every headline for directional crude-price impact — bullish / bearish / neutral.", col: "7C3AED" },
    { title: "Statistical Alerts",  body: "Robust z-score engine (median + MAD) detects anomalies in prices, spreads, CFTC positioning & EIA inventories.", col: AMBER },
    { title: "Shipping Intel",       body: "Live AIS vessel tracking via aisstream.io — chokepoint monitoring, tanker density, and floating storage detection.", col: BEAR },
  ];

  cards.forEach((c, i) => {
    const x = 0.45 + i * 2.32;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.1, w: 2.1, h: 2.85,
      fill: { color: BG_CARD2 }, line: { color: c.col }, shadow: makeShadow()
    });
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 2.1, w: 2.1, h: 0.07,
      fill: { color: c.col }, line: { color: c.col }
    });
    s.addText(c.title, {
      x: x + 0.12, y: 2.22, w: 1.9, h: 0.42,
      fontSize: 12, bold: true, color: WHITE
    });
    s.addText(c.body, {
      x: x + 0.12, y: 2.68, w: 1.88, h: 2.1,
      fontSize: 9.5, color: MUTED, lineSpacingMultiple: 1.4
    });
  });
}

// ══════════════════════════════════════════════════════════════
// SLIDE 3 — Dashboard Overview
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });

  s.addText("MARKET OVERVIEW — DASHBOARD", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  // ── Topbar mock ──
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 1.0, w: 9.1, h: 0.45,
    fill: { color: "0B1222" }, line: { color: BORDER }
  });
  s.addText("HORIZON  ·  Market Overview", {
    x: 0.65, y: 1.02, w: 4, h: 0.4,
    fontSize: 10, bold: true, color: WHITE
  });
  s.addText("UTC  16:42:05   🔔  ⚙   👤", {
    x: 7.2, y: 1.02, w: 2.2, h: 0.4,
    fontSize: 9.5, color: MUTED, align: "right"
  });

  // ── Alerts bar ──
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 1.45, w: 9.1, h: 0.35,
    fill: { color: "0F1A2E" }, line: { color: BORDER }
  });
  s.addText("⚡ ALERTS   |  Brent +2.1σ  [WATCH]  ·  WTI Net Long +2.4σ  [ELEVATED]  ·  Crude Stocks −3.2 mb  [HIGH]", {
    x: 0.6, y: 1.47, w: 8.8, h: 0.3,
    fontSize: 9, color: AMBER
  });

  // ── Price chart block ──
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 1.85, w: 5.9, h: 1.6,
    fill: { color: BG_CARD }, line: { color: BORDER }
  });
  s.addText("Live Price Chart  ·  6 commodities  ·  1D / 1W / 1M / 3M / 1Y", {
    x: 0.6, y: 1.9, w: 5.6, h: 0.3, fontSize: 9, color: TEAL_LT
  });
  // fake chart lines
  const pts = [[0.6,3.0],[1.2,2.85],[1.8,2.95],[2.4,2.7],[3.0,2.55],[3.6,2.68],[4.2,2.5],[4.8,2.42],[5.4,2.58],[5.9,2.48]];
  for (let i = 0; i < pts.length - 1; i++) {
    s.addShape(pres.shapes.LINE, {
      x: pts[i][0], y: pts[i][1], w: pts[i+1][0]-pts[i][0], h: pts[i+1][1]-pts[i][1],
      line: { color: TEAL, width: 1.5 }
    });
  }
  const pts2 = [[0.6,3.1],[1.2,3.0],[1.8,3.05],[2.4,2.9],[3.0,2.75],[3.6,2.82],[4.2,2.68],[4.8,2.6],[5.4,2.7],[5.9,2.62]];
  for (let i = 0; i < pts2.length - 1; i++) {
    s.addShape(pres.shapes.LINE, {
      x: pts2[i][0], y: pts2[i][1], w: pts2[i+1][0]-pts2[i][0], h: pts2[i+1][1]-pts2[i][1],
      line: { color: AMBER, width: 1.5 }
    });
  }

  // ── News feed block ──
  s.addShape(pres.shapes.RECTANGLE, {
    x: 6.45, y: 1.85, w: 3.1, h: 1.6,
    fill: { color: BG_CARD }, line: { color: BORDER }
  });
  s.addText("Breaking News  ·  AI Sentiment Gauge", {
    x: 6.55, y: 1.9, w: 2.9, h: 0.28, fontSize: 9, color: TEAL_LT
  });
  // Sentiment meter bar
  s.addShape(pres.shapes.RECTANGLE, { x: 6.55, y: 2.22, w: 2.88, h: 0.14, fill:{color:"1F2937"}, line:{color:BORDER} });
  s.addShape(pres.shapes.RECTANGLE, { x: 6.55, y: 2.22, w: 1.8,  h: 0.14, fill:{color:BULL}, line:{color:BULL} });
  s.addText("Sentiment: BULLISH  +0.42", { x: 6.55, y: 2.38, w: 2.9, h: 0.22, fontSize: 8.5, color: BULL });
  const newsItems = ["OPEC+ output to hold — geopolitical risk premium up", "Iran export curbs tighten — Hormuz flows at risk", "EIA crude draw of 3.2mb — bullish surprise"];
  newsItems.forEach((n, i) => {
    s.addText("· " + n, { x: 6.55, y: 2.65 + i * 0.24, w: 2.92, h: 0.22, fontSize: 8, color: MUTED });
  });

  // ── Curves row ──
  const curveLabels = ["Forward Curves", "Spreads", "Fly Structure"];
  curveLabels.forEach((label, i) => {
    const x = 0.45 + i * 3.05;
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: 3.53, w: 2.88, h: 1.0,
      fill: { color: BG_CARD }, line: { color: BORDER }
    });
    s.addText(label, { x: x+0.1, y: 3.57, w: 2.7, h: 0.25, fontSize: 9, color: TEAL_LT });
    // mini placeholder chart
    s.addShape(pres.shapes.LINE, { x: x+0.1, y: 4.2, w: 2.5, h: 0, line:{ color: BORDER, width: 0.5 } });
    const ys = i===0 ? [4.35,4.2,4.15,4.1,4.08,4.06,4.05] : i===1 ? [4.35,4.25,4.15,4.2,4.1,4.18,4.12] : [4.2,4.3,4.15,4.35,4.1,4.28,4.08];
    const xs2 = [x+0.1, x+0.5, x+0.9, x+1.3, x+1.7, x+2.1, x+2.5];
    for (let j = 0; j < xs2.length-1; j++) {
      s.addShape(pres.shapes.LINE, { x: xs2[j], y: ys[j], w: xs2[j+1]-xs2[j], h: ys[j+1]-ys[j], line:{ color: i===0?TEAL:i===1?AMBER:BULL, width: 1 } });
    }
  });

  // ── Pointer labels ──
  ptr(s, "Horizontal alert strip — Watch / Elevated / High tiers", 0.45, 1.38, 8.5, AMBER);
  ptr(s, "Live chart: Brent (teal), WTI (amber) — up to 1Y history, 6 symbols", 0.45, 3.43, 5.5);
  ptr(s, "News feed with inline LLM sentiment gauge", 6.2, 3.43, 3.2);
}

// ══════════════════════════════════════════════════════════════
// SLIDE 4 — Live Price Tracker
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });

  s.addText("LIVE PRICE TRACKER", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  // Symbol tiles
  const symbols = [
    { sym: "Brent",  val: "$84.20", chg: "+1.23%", col: TEAL },
    { sym: "WTI",    val: "$80.15", chg: "+0.95%", col: "3B82F6" },
    { sym: "RBOB",   val: "$2.641", chg: "+1.40%", col: AMBER },
    { sym: "Heating Oil", val: "$2.512", chg: "+0.82%", col: "A855F7" },
    { sym: "Dubai",  val: "$82.20", chg: "+1.18%", col: "F97316" },
  ];
  symbols.forEach((sym, i) => {
    const x = 0.45 + i * 1.84;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.0, w: 1.72, h: 0.9, fill:{color:BG_CARD2}, line:{color:sym.col}, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.0, w: 1.72, h: 0.06, fill:{color:sym.col}, line:{color:sym.col} });
    s.addText(sym.sym, { x, y: 1.08, w: 1.72, h: 0.28, fontSize: 9.5, color: MUTED, align:"center" });
    s.addText(sym.val, { x, y: 1.34, w: 1.72, h: 0.35, fontSize: 16, bold:true, color: WHITE, align:"center" });
    s.addText(sym.chg, { x, y: 1.67, w: 1.72, h: 0.2, fontSize: 9, color: BULL, align:"center" });
  });

  // Chart area (mock)
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.45, y: 2.02, w: 9.1, h: 2.7,
    fill: { color: BG_CARD }, line: { color: BORDER }
  });
  s.addText("Interactive price chart  ·  Time range: 1D / 1W / 1M / 3M / 1Y  ·  Select any commodity", {
    x: 0.6, y: 2.08, w: 8, h: 0.28, fontSize: 9.5, color: TEAL_LT
  });
  // fake chart
  const chartPts = [
    [0.6,4.3],[1.2,4.1],[1.9,4.2],[2.6,3.9],[3.2,3.7],[3.9,3.8],[4.5,3.55],[5.2,3.4],[5.8,3.55],[6.4,3.35],[7.0,3.2],[7.6,3.3],[8.2,3.1],[8.8,3.0],[9.4,2.95]
  ];
  for (let i = 0; i < chartPts.length-1; i++) {
    s.addShape(pres.shapes.LINE, { x: chartPts[i][0], y: chartPts[i][1], w: chartPts[i+1][0]-chartPts[i][0], h: chartPts[i+1][1]-chartPts[i][1], line:{ color: TEAL, width: 2 } });
  }
  // grid lines
  for (let g = 0; g < 3; g++) {
    s.addShape(pres.shapes.LINE, { x: 0.6, y: 2.7 + g*0.55, w: 8.8, h: 0, line:{ color: BORDER, width: 0.5 } });
  }

  // Feature bullets
  const feats = [
    "6 commodities: Brent, WTI, RBOB, Heating Oil, Nat Gas, Dubai Crude",
    "Dubai Crude = synthetic proxy (Brent − $2.00 EFS spread) — clearly labeled 'Indicative'",
    "Up to 1 year of daily OHLC history pulled from Yahoo Finance",
    "Candlestick + area modes, time-range selector, hover crosshair",
  ];
  feats.forEach((f, i) => {
    ptr(s, f, 0.45, 4.83 + i * 0.0, 9.0);
  });
  s.addText(feats.join("\n"), {
    x: 0.45, y: 4.82, w: 9.1, h: 0.65,
    fontSize: 9, color: MUTED, lineSpacingMultiple: 1.45
  });
}

// ══════════════════════════════════════════════════════════════
// SLIDE 5 — Forward Curves
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });

  s.addText("FORWARD CURVES", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  s.addText(
    "Full term-structure visualisation for all five commodities — M1 through M12+ contracts plotted on a single chart.",
    { x: 0.45, y: 0.96, w: 9.1, h: 0.35, fontSize: 11, color: MUTED }
  );

  // Mock curve chart
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 1.42, w: 5.8, h: 3.3, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("Forward Curve  ·  Brent Crude  ·  Backwardation (spot > deferred)", {
    x: 0.6, y: 1.5, w: 5.5, h: 0.28, fontSize: 9.5, color: TEAL_LT
  });
  // Backwardated curve shape
  const cPts = [[0.65,2.0],[1.3,2.2],[1.95,2.45],[2.6,2.65],[3.25,2.85],[3.9,3.05],[4.55,3.2],[5.1,3.32],[5.6,3.4]];
  for (let i = 0; i < cPts.length-1; i++) {
    s.addShape(pres.shapes.LINE, { x: cPts[i][0], y: cPts[i][1], w: cPts[i+1][0]-cPts[i][0], h: cPts[i+1][1]-cPts[i][1], line:{ color: TEAL, width: 2 } });
  }
  // Contango curve
  const cPts2 = [[0.65,2.4],[1.3,2.5],[1.95,2.55],[2.6,2.58],[3.25,2.6],[3.9,2.6],[4.55,2.58],[5.1,2.55],[5.6,2.52]];
  for (let i = 0; i < cPts2.length-1; i++) {
    s.addShape(pres.shapes.LINE, { x: cPts2[i][0], y: cPts2[i][1], w: cPts2[i+1][0]-cPts2[i][0], h: cPts2[i+1][1]-cPts2[i][1], line:{ color: AMBER, width: 2 } });
  }
  // Legend
  s.addShape(pres.shapes.LINE, { x: 0.75, y: 4.45, w: 0.35, h: 0, line:{color:TEAL,width:2} });
  s.addText("Current (Backwardated)", { x: 1.15, y: 4.38, w: 2.2, h: 0.25, fontSize: 9, color: MUTED });
  s.addShape(pres.shapes.LINE, { x: 0.75, y: 4.65, w: 0.35, h: 0, line:{color:AMBER,width:2} });
  s.addText("Prior week (Flat)", { x: 1.15, y: 4.58, w: 2.2, h: 0.25, fontSize: 9, color: MUTED });

  // Right panel — features
  s.addShape(pres.shapes.RECTANGLE, { x: 6.4, y: 1.42, w: 3.15, h: 3.3, fill:{color:BG_CARD2}, line:{color:BORDER} });

  const items = [
    ["Commodities", "Brent · WTI · RBOB · Heating Oil · Gas Oil"],
    ["Data Source",  "ICE settlement CSVs (Brent/Gas Oil)\nYahoo contract-month tickers (others)"],
    ["Structure",    "Backwardation = bull signal (low stocks)\nContango = bearish / oversupply"],
    ["Refresh",      "5-min server cache, demand-pulled by frontend"],
    ["Selectable",   "Commodity dropdown on Dashboard & Crude tab"],
  ];
  items.forEach(([k, v], i) => {
    s.addText(k, { x: 6.55, y: 1.58 + i*0.62, w: 2.9, h: 0.25, fontSize: 10, bold: true, color: TEAL_LT });
    s.addText(v, { x: 6.55, y: 1.81 + i*0.62, w: 2.9, h: 0.35, fontSize: 9, color: MUTED, lineSpacingMultiple: 1.3 });
  });
}

// ══════════════════════════════════════════════════════════════
// SLIDE 6 — Spreads & Butterflies
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });

  s.addText("SPREADS & BUTTERFLY MONITOR", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  s.addText("Calendar spreads and fly structures for all 5 commodities — key signals for term-structure positioning and roll analysis.", {
    x: 0.45, y: 0.96, w: 9.1, h: 0.35, fontSize: 11, color: MUTED
  });

  // Two mock cards side by side
  // Spreads card
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 1.42, w: 4.4, h: 3.5, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("CALENDAR SPREADS", { x: 0.6, y: 1.5, w: 4, h: 0.28, fontSize: 10, bold:true, color: TEAL_LT });
  const spreadTabs = ["M1-M2", "M1-M6", "M1-M12"];
  spreadTabs.forEach((t, i) => {
    const active = i === 0;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6+i*1.12, y: 1.82, w: 1.05, h: 0.24, fill:{color: active?TEAL:BG_CARD2}, line:{color:TEAL} });
    s.addText(t, { x: 0.6+i*1.12, y: 1.82, w: 1.05, h: 0.24, fontSize: 8.5, color: active?"FFFFFF":MUTED, align:"center", valign:"middle", margin:0 });
  });
  // Spread chart
  const sPts = [[0.6,3.5],[1.0,3.3],[1.4,3.5],[1.8,3.2],[2.2,3.0],[2.6,3.15],[3.0,2.9],[3.4,2.7],[3.8,2.85],[4.2,2.6],[4.6,2.75]];
  for (let i = 0; i < sPts.length-1; i++) {
    s.addShape(pres.shapes.LINE, { x: sPts[i][0], y: sPts[i][1], w: sPts[i+1][0]-sPts[i][0], h: sPts[i+1][1]-sPts[i][1], line:{ color: TEAL, width: 1.5 } });
  }
  s.addShape(pres.shapes.LINE, { x: 0.6, y: 4.3, w: 4.0, h: 0, line:{color:BORDER,width:0.5} });
  s.addText("Last: $1.82  ·  Backwardation strengthening", { x: 0.6, y: 4.36, w: 4.1, h: 0.25, fontSize: 8.5, color: BULL });
  ptr(s, "M1-M2 = nearest spread, key roll cost indicator", 0.45, 4.65, 4.5);
  ptr(s, "M1-M6 / M1-M12 = term structure steepness", 0.45, 4.88, 4.5);

  // Fly card
  s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y: 1.42, w: 4.55, h: 3.5, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("BUTTERFLY STRUCTURES", { x: 5.15, y: 1.5, w: 4.2, h: 0.28, fontSize: 10, bold:true, color: AMBER });
  const flyTabs = ["1-2-3", "2-3-4", "4-5-6"];
  flyTabs.forEach((t, i) => {
    const active = i === 0;
    s.addShape(pres.shapes.RECTANGLE, { x: 5.15+i*1.12, y: 1.82, w: 1.05, h: 0.24, fill:{color: active?AMBER:BG_CARD2}, line:{color:AMBER} });
    s.addText(t, { x: 5.15+i*1.12, y: 1.82, w: 1.05, h: 0.24, fontSize: 8.5, color: active?"0F172A":MUTED, align:"center", valign:"middle", margin:0 });
  });
  // Fly chart (oscillating — expected for butterfly)
  const fPts = [[5.15,3.0],[5.55,2.75],[5.95,3.2],[6.35,2.8],[6.75,3.3],[7.15,2.7],[7.55,3.1],[7.95,2.65],[8.35,3.0],[8.75,2.7],[9.2,3.05]];
  for (let i = 0; i < fPts.length-1; i++) {
    s.addShape(pres.shapes.LINE, { x: fPts[i][0], y: fPts[i][1], w: fPts[i+1][0]-fPts[i][0], h: fPts[i+1][1]-fPts[i][1], line:{ color: AMBER, width: 1.5 } });
  }
  s.addShape(pres.shapes.LINE, { x: 5.15, y: 4.3, w: 4.35, h: 0, line:{color:BORDER,width:0.5} });
  s.addShape(pres.shapes.LINE, { x: 5.15, y: 2.85, w: 4.35, h: 0, line:{color:"1E3A5F",width:0.5, dashType:"dash"} });
  s.addText("Last: +$0.24  ·  Mild kink at front of curve", { x: 5.15, y: 4.36, w: 4.2, h: 0.25, fontSize: 8.5, color: AMBER });
  ptr(s, "Fly = M1 − 2×M2 + M3  (curvature, not direction)", 5.0, 4.65, 4.5);
  ptr(s, "Positive fly = front months rich relative to middle", 5.0, 4.88, 4.5);
}

// ══════════════════════════════════════════════════════════════
// SLIDE 7 — AI News Sentiment
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:"7C3AED"}, line:{color:"7C3AED"} });

  s.addText("AI NEWS SENTIMENT INTELLIGENCE", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  // Pipeline flow
  const steps = ["RSS Feeds\n(FinancialJuice\n+ OilPrice.com)", "Energy\nFilter &\nDedup", "Groq LLM\n(LLaMA 3.3-70B)\nBatch Score", "Persistent\nStore\n(40-item queue)", "Sentiment\nGauge\n+ News Feed"];
  const stepColors = ["1E3A5F", "1E3A5F", "7C3AED", "1E3A5F", TEAL];
  steps.forEach((text, i) => {
    const x = 0.45 + i * 1.84;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.0, w: 1.65, h: 0.85, fill:{color:stepColors[i]}, line:{color:i===2?"7C3AED":BORDER}, shadow: makeShadow() });
    s.addText(text, { x, y: 1.0, w: 1.65, h: 0.85, fontSize: 8.5, color: WHITE, align:"center", valign:"middle", lineSpacingMultiple: 1.3 });
    if (i < steps.length-1) {
      s.addShape(pres.shapes.LINE, { x: x+1.65, y: 1.425, w: 0.19, h: 0, line:{color:TEAL,width:1.5} });
      s.addText("▶", { x: x+1.78, y: 1.32, w: 0.18, h: 0.25, fontSize: 9, color: TEAL, align:"center" });
    }
  });

  // Score examples
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 2.02, w: 5.5, h: 2.65, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("REAL EXAMPLE SCORES  (Groq / LLaMA 3.3-70B)", { x: 0.6, y: 2.1, w: 5.2, h: 0.28, fontSize: 10, bold:true, color: "7C3AED" });

  const examples = [
    { headline: "Trump to impose sanctions targeting Iran oil sector", impact: "+0.90", theme:"Geopolitics", kind:"event", color: BULL },
    { headline: "Traders shorting Hormuz — crisis seen as over", impact: "−0.30", theme:"Geopolitics", kind:"opinion", color: BEAR },
    { headline: "OPEC production falls by 800k bbl/d in April",   impact: "+0.60", theme:"Supply",       kind:"event", color: BULL },
    { headline: "Central bank hikes signal demand slowdown",       impact: "−0.22", theme:"Macro",        kind:"forecast", color: BEAR },
    { headline: "Analyst says fake-news driving oil volatility",  impact: "0.00",  theme:"Macro",        kind:"opinion", color: MUTED },
  ];
  examples.forEach((ex, i) => {
    const y = 2.48 + i * 0.42;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.55, y: y-0.02, w: 5.25, h: 0.36, fill:{color:BG_CARD2}, line:{color:BORDER} });
    s.addText(ex.impact, { x: 0.6, y, w: 0.6, h: 0.28, fontSize: 11, bold:true, color: ex.color, align:"center" });
    s.addText(ex.headline, { x: 1.25, y, w: 3.2, h: 0.28, fontSize: 8.5, color: WHITE });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.5, y: y+0.02, w: 0.65, h: 0.2, fill:{color:"1F2937"}, line:{color:"374151"}, rectRadius:0.03 });
    s.addText(ex.theme, { x: 4.5, y: y+0.02, w: 0.65, h: 0.2, fontSize: 7, color: MUTED, align:"center", valign:"middle", margin:0 });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.18, y: y+0.02, w: 0.56, h: 0.2, fill:{color:"1F2937"}, line:{color:"374151"}, rectRadius:0.03 });
    s.addText(ex.kind, { x: 5.18, y: y+0.02, w: 0.56, h: 0.2, fontSize: 7, color: MUTED, align:"center", valign:"middle", margin:0 });
  });

  // Right panel — key design decisions
  s.addShape(pres.shapes.RECTANGLE, { x: 6.1, y: 2.02, w: 3.45, h: 2.65, fill:{color:BG_CARD2}, line:{color:BORDER} });
  s.addText("KEY DESIGN DECISIONS", { x: 6.25, y: 2.1, w: 3.2, h: 0.28, fontSize: 10, bold:true, color: TEAL_LT });

  const decisions = [
    ["Directional, not tonal", "Scores crude price IMPACT — a refinery fire is bearish crude, not \"negative news\""],
    ["Score-only-new", "Persistent 40-item queue — already-scored headlines are never re-sent to the LLM"],
    ["Offline fallback", "Lexicon scorer (22 oil-market phrases) activates if LLM API is unavailable"],
    ["Dedup via event_key", "SHA1(day + keywords) collapses near-duplicate headlines from multiple feeds"],
  ];
  decisions.forEach(([k, v], i) => {
    s.addText(k, { x: 6.25, y: 2.48 + i*0.58, w: 3.2, h: 0.25, fontSize: 9.5, bold:true, color: "A78BFA" });
    s.addText(v, { x: 6.25, y: 2.71 + i*0.58, w: 3.2, h: 0.32, fontSize: 8.5, color: MUTED, lineSpacingMultiple: 1.3 });
  });
}

// ══════════════════════════════════════════════════════════════
// SLIDE 8 — Statistical Alerts (Z-Score)
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:AMBER}, line:{color:AMBER} });

  s.addText("STATISTICAL ANOMALY ALERTS (Z-SCORE)", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 22, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  s.addText("A robust statistical engine flags when any metric deviates significantly from its recent distribution — not just price levels, but spreads, positioning, and inventories.", {
    x: 0.45, y: 0.96, w: 9.1, h: 0.38, fontSize: 10.5, color: MUTED
  });

  // 3 tier cards
  const tiers = [
    { label:"WATCH",    z:"±1.5σ", color:"F59E0B", desc:"Early-warning — metric approaching unusual territory. Monitor closely." },
    { label:"ELEVATED", z:"±2.0σ", color:"F97316", desc:"Statistically rare (top 5%). Review for risk management implications." },
    { label:"HIGH",     z:"±3.0σ", color:BEAR,    desc:"Extreme outlier — less than 0.3% probability. Act immediately." },
  ];
  tiers.forEach((t, i) => {
    const x = 0.45 + i * 3.05;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.48, w: 2.88, h: 1.25, fill:{color:BG_CARD2}, line:{color:t.color}, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.48, w: 2.88, h: 0.06, fill:{color:t.color}, line:{color:t.color} });
    s.addText(t.label, { x, y: 1.56, w: 2.88, h: 0.3, fontSize: 13, bold:true, color: t.color, align:"center" });
    s.addText(t.z, { x, y: 1.84, w: 2.88, h: 0.3, fontSize: 20, bold:true, color: WHITE, align:"center" });
    s.addText(t.desc, { x: x+0.1, y: 2.14, w: 2.7, h: 0.55, fontSize: 8.5, color: MUTED, align:"center", lineSpacingMultiple:1.3 });
  });

  // Tier A & B
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 2.88, w: 4.55, h: 2.3, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("TIER A  ·  Stationary / Mean-Reverting", { x: 0.6, y: 2.95, w: 4.2, h: 0.28, fontSize: 10, bold:true, color: TEAL_LT });
  const tierA = ["% daily moves — Brent, WTI, RBOB, Heating Oil  (252d returns)", "Calendar spreads — Brent-WTI, RBOB-Brent, 3:2:1 Crack  (120d levels)", "CFTC managed-money net positions — WTI & Brent  (full history)"];
  tierA.forEach((t, i) => s.addText("· " + t, { x: 0.6, y: 3.3 + i*0.52, w: 4.3, h: 0.45, fontSize: 9, color: MUTED, lineSpacingMultiple:1.3 }));

  s.addShape(pres.shapes.RECTANGLE, { x: 5.1, y: 2.88, w: 4.45, h: 2.3, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("TIER B  ·  Rolling / Level-Based", { x: 5.25, y: 2.95, w: 4.1, h: 0.28, fontSize: 10, bold:true, color: AMBER });
  const tierB = ["Price stretch — 60d rolling Bollinger-style z-score on price level", "EIA inventory w/w change — crude / gasoline / distillate  (weekly ΔMb)", "Robust estimator: Median + MAD×1.4826  (outlier-resistant)"];
  tierB.forEach((t, i) => s.addText("· " + t, { x: 5.25, y: 3.3 + i*0.52, w: 4.2, h: 0.45, fontSize: 9, color: MUTED, lineSpacingMultiple:1.3 }));

  ptr(s, "Hysteresis prevents alert flapping at threshold boundaries (±0.3σ buffer)", 0.45, 5.08, 9.0, AMBER);
}

// ══════════════════════════════════════════════════════════════
// SLIDE 9 — Crude Oil Tab
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });

  s.addText("CRUDE OIL DEEP-DIVE TAB", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  s.addText("Dedicated Crude Oil page — full term structure analysis, spread history, and butterfly signals in one focused view.", {
    x: 0.45, y: 0.96, w: 9.1, h: 0.35, fontSize: 11, color: MUTED
  });

  // Layout mock
  // Forward curve card
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 1.42, w: 9.1, h: 1.25, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("Forward Curve  ·  WTI  (default, selectable)", { x: 0.6, y: 1.5, w: 5, h: 0.28, fontSize: 9.5, color: TEAL_LT });
  const cp = [[0.7,2.3],[1.3,2.45],[1.9,2.6],[2.5,2.7],[3.1,2.8],[3.7,2.87],[4.3,2.92],[4.9,2.95],[5.5,2.97],[6.1,2.98],[6.7,2.99],[7.3,3.0],[7.9,3.0],[8.6,3.0],[9.2,3.0]];
  for (let i = 0; i < cp.length-1; i++) s.addShape(pres.shapes.LINE, { x: cp[i][0], y: cp[i][1], w: cp[i+1][0]-cp[i][0], h: cp[i+1][1]-cp[i][1], line:{color:TEAL,width:1.5} });
  s.addShape(pres.shapes.OVAL, { x: 0.65, y: 2.25, w: 0.1, h: 0.1, fill:{color:TEAL}, line:{color:TEAL} });

  // Spread card
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 2.78, w: 4.4, h: 2.4, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("Calendar Spreads  ·  WTI", { x: 0.6, y: 2.86, w: 4.1, h: 0.28, fontSize: 9.5, color: TEAL_LT });
  const spts = [[0.6,4.3],[1.0,4.1],[1.4,4.25],[1.8,3.95],[2.2,3.75],[2.6,3.9],[3.0,3.65],[3.4,3.45],[3.8,3.6],[4.2,3.35],[4.6,3.5]];
  for (let i = 0; i < spts.length-1; i++) s.addShape(pres.shapes.LINE, { x: spts[i][0], y: spts[i][1], w: spts[i+1][0]-spts[i][0], h: spts[i+1][1]-spts[i][1], line:{color:TEAL,width:1.5} });
  s.addText("M1-M2  ·  Last: $1.55  ·  Strengthening backwardation", { x: 0.6, y: 4.92, w: 4.1, h: 0.22, fontSize: 8.5, color: BULL });

  // Fly card
  s.addShape(pres.shapes.RECTANGLE, { x: 5.0, y: 2.78, w: 4.55, h: 2.4, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("Butterfly Structure  ·  WTI", { x: 5.15, y: 2.86, w: 4.2, h: 0.28, fontSize: 9.5, color: AMBER });
  const fpts = [[5.2,3.9],[5.6,3.65],[6.0,4.1],[6.4,3.7],[6.8,4.2],[7.2,3.6],[7.6,4.05],[8.0,3.55],[8.4,3.9],[8.8,3.6],[9.2,3.85]];
  for (let i = 0; i < fpts.length-1; i++) s.addShape(pres.shapes.LINE, { x: fpts[i][0], y: fpts[i][1], w: fpts[i+1][0]-fpts[i][0], h: fpts[i+1][1]-fpts[i][1], line:{color:AMBER,width:1.5} });
  s.addShape(pres.shapes.LINE, { x: 5.2, y: 3.88, w: 4.3, h: 0, line:{color:"1E3A5F",width:0.5,dashType:"dash"} });
  s.addText("1-2-3 Fly  ·  Last: +$0.30  ·  Front month curvature elevated", { x: 5.15, y: 4.92, w: 4.3, h: 0.22, fontSize: 8.5, color: AMBER });
}

// ══════════════════════════════════════════════════════════════
// SLIDE 10 — News Page & Additional Pages
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:"7C3AED"}, line:{color:"7C3AED"} });

  s.addText("NEWS PAGE  &  OTHER SECTIONS", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  // News page mock
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 1.02, w: 5.6, h: 3.85, fill:{color:BG_CARD}, line:{color:BORDER} });
  s.addText("NEWS PAGE", { x: 0.6, y: 1.1, w: 5, h: 0.28, fontSize: 10, bold:true, color: "A78BFA" });

  // Sentiment gauge mock
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.45, w: 5.2, h: 0.7, fill:{color:BG_CARD2}, line:{color:"7C3AED"} });
  s.addText("Market Sentiment Gauge", { x: 0.75, y: 1.5, w: 2.5, h: 0.22, fontSize: 9, color: MUTED });
  s.addText("BULLISH  +0.42", { x: 0.75, y: 1.7, w: 1.5, h: 0.3, fontSize: 12, bold:true, color: BULL });
  s.addShape(pres.shapes.RECTANGLE, { x: 2.5, y: 1.67, w: 3.0, h: 0.18, fill:{color:"1F2937"}, line:{color:BORDER} });
  s.addShape(pres.shapes.RECTANGLE, { x: 2.5, y: 1.67, w: 1.9, h: 0.18, fill:{color:BULL}, line:{color:BULL} });
  s.addText("62% Bull · 23% Bear · 15% Neutral  (21 headlines, 24h decay)", { x: 2.5, y: 1.87, w: 3.2, h: 0.2, fontSize: 7.5, color: MUTED });

  // News items
  const nItems = [
    { h:"Trump sanctions target Iranian crude exports", tag:"Geopolitics", impact:"+0.90", c: BULL },
    { h:"OPEC April output falls below quota target",  tag:"Supply",       impact:"+0.60", c: BULL },
    { h:"EIA crude stockpile falls 3.2 mb — surprise draw", tag:"Inventory", impact:"+0.42", c: BULL },
    { h:"Fed signals further rate hikes — demand concern",  tag:"Macro",    impact:"−0.22", c: BEAR },
    { h:"Traders covering Hormuz shorts — risk premium fades", tag:"Geopolitics", impact:"−0.30", c: BEAR },
  ];
  nItems.forEach((ni, i) => {
    const y = 2.25 + i * 0.44;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y, w: 5.2, h: 0.38, fill:{color:"0D1B2E"}, line:{color:BORDER} });
    s.addText(ni.impact, { x: 0.65, y: y+0.05, w: 0.55, h: 0.28, fontSize: 10, bold:true, color: ni.c, align:"center" });
    s.addText(ni.h, { x: 1.24, y: y+0.05, w: 3.55, h: 0.28, fontSize: 8.5, color: WHITE });
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 4.82, y: y+0.08, w: 0.85, h: 0.18, fill:{color:"1F2937"}, line:{color:"374151"}, rectRadius:0.03 });
    s.addText(ni.tag, { x: 4.82, y: y+0.08, w: 0.85, h: 0.18, fontSize: 7, color: MUTED, align:"center", valign:"middle", margin:0 });
  });

  // Right: other pages
  const pages = [
    { name: "Alerts", desc: "Active alert board grouped by tier (Watch / Elevated / High). Click any alert for drill-down.", color: AMBER },
    { name: "Shipping", desc: "Live AIS tanker map via aisstream.io. Vessel density, chokepoints (Hormuz, Suez, Bab-el-Mandeb), VLCC tracking.", color: "3B82F6" },
    { name: "Correlations", desc: "Cross-commodity correlation matrix with rolling windows. Identifies regime shifts.", color: TEAL },
    { name: "Rig Count", desc: "Baker Hughes NA & International rig count trends — leading indicator for crude production.", color: "10B981" },
    { name: "Macro / Calendar", desc: "CFTC COT positioning charts + economic release calendar. Macro context for oil prices.", color: "A855F7" },
  ];
  pages.forEach((p, i) => {
    const y = 1.02 + i * 0.77;
    s.addShape(pres.shapes.RECTANGLE, { x: 6.2, y, w: 3.35, h: 0.65, fill:{color:BG_CARD2}, line:{color:p.color}, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x: 6.2, y, w: 0.07, h: 0.65, fill:{color:p.color}, line:{color:p.color} });
    s.addText(p.name, { x: 6.35, y: y+0.04, w: 3.1, h: 0.26, fontSize: 11, bold:true, color: WHITE });
    s.addText(p.desc, { x: 6.35, y: y+0.3, w: 3.1, h: 0.32, fontSize: 8, color: MUTED, lineSpacingMultiple: 1.2 });
  });
}

// ══════════════════════════════════════════════════════════════
// SLIDE 11 — Shipping Intelligence
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:"3B82F6"}, line:{color:"3B82F6"} });

  s.addText("LIVE SHIPPING INTELLIGENCE", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  // Map placeholder
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 1.02, w: 6.0, h: 3.65, fill:{color:"0B1628"}, line:{color:"1E3A5F"} });
  s.addText("Live AIS Tanker Map", { x: 0.6, y: 1.12, w: 5.6, h: 0.3, fontSize: 10, bold:true, color: "7DD3FC" });

  // Fake map grid lines
  for (let g = 0; g < 5; g++) {
    s.addShape(pres.shapes.LINE, { x: 0.5, y: 1.6 + g*0.55, w: 5.9, h: 0, line:{color:"0F2744",width:0.5} });
    s.addShape(pres.shapes.LINE, { x: 0.5 + g*1.1, y: 1.42, w: 0, h: 3.2, line:{color:"0F2744",width:0.5} });
  }

  // Chokepoint markers
  const cpts = [
    { x: 4.6, y: 2.2, label:"Hormuz", c: BEAR },
    { x: 2.5, y: 2.0, label:"Suez",   c: AMBER },
    { x: 3.2, y: 2.8, label:"Bab-el-Mandeb", c: AMBER },
    { x: 1.2, y: 2.5, label:"Gibraltar", c: TEAL },
  ];
  cpts.forEach(cp => {
    s.addShape(pres.shapes.OVAL, { x: cp.x-0.08, y: cp.y-0.08, w: 0.16, h: 0.16, fill:{color:cp.c}, line:{color:cp.c} });
    s.addText(cp.label, { x: cp.x+0.1, y: cp.y-0.1, w: 1.2, h: 0.22, fontSize: 7.5, color: cp.c });
  });

  // Fake vessel dots
  const vessels = [[1.0,2.9],[1.8,2.3],[2.2,3.1],[3.8,2.4],[4.0,3.0],[4.8,2.7],[5.5,2.1],[0.9,3.3],[2.9,2.0],[3.3,3.2]];
  vessels.forEach(([vx, vy]) => {
    s.addShape(pres.shapes.OVAL, { x: vx-0.04, y: vy-0.04, w: 0.08, h: 0.08, fill:{color:"7DD3FC"}, line:{color:"7DD3FC"} });
  });

  // Legend
  s.addShape(pres.shapes.OVAL, { x: 0.6, y: 4.44, w: 0.1, h: 0.1, fill:{color:"7DD3FC"}, line:{color:"7DD3FC"} });
  s.addText("VLCC / Tanker", { x: 0.75, y: 4.4, w: 1.5, h: 0.22, fontSize: 8.5, color: MUTED });
  s.addShape(pres.shapes.OVAL, { x: 2.6, y: 4.44, w: 0.1, h: 0.1, fill:{color:BEAR}, line:{color:BEAR} });
  s.addText("High-risk chokepoint", { x: 2.75, y: 4.4, w: 1.6, h: 0.22, fontSize: 8.5, color: MUTED });
  s.addShape(pres.shapes.OVAL, { x: 4.7, y: 4.44, w: 0.1, h: 0.1, fill:{color:AMBER}, line:{color:AMBER} });
  s.addText("Watch chokepoint", { x: 4.85, y: 4.4, w: 1.5, h: 0.22, fontSize: 8.5, color: MUTED });

  // Right panel
  s.addShape(pres.shapes.RECTANGLE, { x: 6.6, y: 1.02, w: 2.95, h: 3.65, fill:{color:BG_CARD2}, line:{color:BORDER} });
  s.addText("AIS INTEL FEATURES", { x: 6.75, y: 1.12, w: 2.7, h: 0.28, fontSize: 10, bold:true, color: "7DD3FC" });

  const features = [
    ["Real-time AIS", "Live vessel stream via aisstream.io WebSocket — VLCCs, supertankers, product tankers"],
    ["Chokepoints", "Hormuz · Suez · Bab-el-Mandeb · Malacca · Gibraltar — vessel density monitoring"],
    ["Floating Storage", "Detect tankers stationary >24h — key signal for physical market tightness"],
    ["Auto-disconnect", "Vessels not heard from in 1hr are evicted — map stays clean and current"],
  ];
  features.forEach(([k, v], i) => {
    s.addShape(pres.shapes.RECTANGLE, { x: 6.65, y: 1.52 + i*0.76, w: 2.82, h: 0.06, fill:{color:"3B82F6"}, line:{color:"3B82F6"} });
    s.addText(k, { x: 6.75, y: 1.6 + i*0.76, w: 2.7, h: 0.25, fontSize: 9.5, bold:true, color: WHITE });
    s.addText(v, { x: 6.75, y: 1.84 + i*0.76, w: 2.7, h: 0.38, fontSize: 8.5, color: MUTED, lineSpacingMultiple: 1.3 });
  });

  ptr(s, "AIS key gitignored — never committed to repo", 0.45, 5.1, 9.0, MUTED);
}

// ══════════════════════════════════════════════════════════════
// SLIDE 12 — Technical Architecture
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });

  s.addText("TECHNICAL ARCHITECTURE", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  // Three tier boxes: Frontend | Backend | Data Sources
  const tiers = [
    {
      title: "Frontend", color: "3B82F6",
      items: ["React 18 + TypeScript", "Vite + TanStack Query", "Recharts / Chart.js", "Tailwind CSS", "React Router", "createPortal topbar injection"]
    },
    {
      title: "Backend", color: TEAL,
      items: ["FastAPI (Python 3.11)", "TTLCache + disk JSON stores", "EIA API v2", "CFTC Socrata API", "Baker Hughes scraper", "aisstream.io WebSocket"]
    },
    {
      title: "Intelligence Layer", color: "7C3AED",
      items: ["Groq LLM (LLaMA 3.3-70B)", "Lexicon fallback scorer", "40-item persistent news queue", "Robust z-score (MAD)", "Hysteresis tier engine", "event_key semantic dedup"]
    },
  ];

  tiers.forEach((tier, i) => {
    const x = 0.45 + i * 3.1;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.02, w: 2.95, h: 3.85, fill:{color:BG_CARD}, line:{color:tier.color}, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.02, w: 2.95, h: 0.36, fill:{color:tier.color}, line:{color:tier.color} });
    s.addText(tier.title.toUpperCase(), { x, y: 1.02, w: 2.95, h: 0.36, fontSize: 11, bold:true, color: "FFFFFF", align:"center", valign:"middle", margin:0 });
    tier.items.forEach((item, j) => {
      s.addShape(pres.shapes.LINE, { x: x+0.18, y: 1.54+j*0.55, w: 0.1, h: 0, line:{color:tier.color,width:2} });
      s.addText(item, { x: x+0.32, y: 1.46+j*0.55, w: 2.55, h: 0.46, fontSize: 9.5, color: MUTED, lineSpacingMultiple:1.3 });
    });
  });

  // Arrows
  s.addShape(pres.shapes.LINE, { x: 3.4, y: 3.0, w: 0.5, h: 0, line:{color:TEAL,width:1.5} });
  s.addText("REST", { x: 3.4, y: 2.82, w: 0.5, h: 0.22, fontSize: 7.5, color: MUTED, align:"center" });
  s.addShape(pres.shapes.LINE, { x: 6.5, y: 3.0, w: 0.5, h: 0, line:{color:"7C3AED",width:1.5} });
  s.addText("calls", { x: 6.5, y: 2.82, w: 0.5, h: 0.22, fontSize: 7.5, color: MUTED, align:"center" });

  // Bottom key numbers
  const nums = [
    { val: "16",  label: "Z-score metrics" },
    { val: "40",  label: "News queue size" },
    { val: "5",   label: "Commodities tracked" },
    { val: "2",   label: "LLM providers" },
  ];
  nums.forEach((n, i) => {
    const x = 0.45 + i * 2.38;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 4.97, w: 2.25, h: 0.5, fill:{color:BG_CARD2}, line:{color:BORDER} });
    s.addText(n.val, { x, y: 4.98, w: 2.25, h: 0.28, fontSize: 18, bold:true, color: TEAL_LT, align:"center" });
    s.addText(n.label, { x, y: 5.2, w: 2.25, h: 0.22, fontSize: 8.5, color: MUTED, align:"center" });
  });
}

// ══════════════════════════════════════════════════════════════
// SLIDE 13 — Roadmap & Close
// ══════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: BG_DARK };
  s.addShape(pres.shapes.RECTANGLE, { x:0, y:0, w:0.06, h:5.625, fill:{color:TEAL}, line:{color:TEAL} });

  s.addText("WHAT'S NEXT  ·  ROADMAP", {
    x: 0.45, y: 0.28, w: 9, h: 0.5,
    fontSize: 24, bold: true, color: WHITE, charSpacing: 2
  });
  hr(s, 0.86);

  const lanes = [
    {
      title: "Phase 2 — Alerts", color: AMBER,
      items: ["Wire z-score metrics into AlertsProvider", "Alerts.tsx statistical anomaly section", "Server-side push (email / Telegram)", "Mobile notification support"]
    },
    {
      title: "Phase 2 — Intelligence", color: "7C3AED",
      items: ["Fair-value model (spread z-score + COT + inventory)", "PADD-level regional inventory stocks", "Weather impact overlay", "EUR/USD + CPI macro tiles"]
    },
    {
      title: "Phase 2 — Shipping", color: "3B82F6",
      items: ["7d / 30d chokepoint history charts", "Floating storage detection algorithm", "Route-level vessel density", "Cargo type classification (VLCC / MR / Aframax)"]
    },
  ];

  lanes.forEach((lane, i) => {
    const x = 0.45 + i * 3.1;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.08, w: 2.95, h: 3.5, fill:{color:BG_CARD2}, line:{color:lane.color}, shadow: makeShadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 1.08, w: 2.95, h: 0.34, fill:{color:lane.color}, line:{color:lane.color} });
    s.addText(lane.title.toUpperCase(), { x, y: 1.08, w: 2.95, h: 0.34, fontSize: 9.5, bold:true, color: "FFFFFF", align:"center", valign:"middle", margin:0 });
    lane.items.forEach((item, j) => {
      s.addText("→  " + item, { x: x+0.18, y: 1.54 + j*0.68, w: 2.7, h: 0.6, fontSize: 9.5, color: MUTED, lineSpacingMultiple:1.3 });
    });
  });

  // Closing line
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 4.75, w: 9.1, h: 0.68, fill:{color:BG_CARD}, line:{color:TEAL} });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.45, y: 4.75, w: 9.1, h: 0.05, fill:{color:TEAL}, line:{color:TEAL} });
  s.addText("HORIZON — from raw data feeds to actionable intelligence, end-to-end.", {
    x: 0.65, y: 4.84, w: 8.7, h: 0.48,
    fontSize: 13, color: TEAL_LT, align: "center", valign: "middle", italic: true
  });
}

// ══════════════════════════════════════════════════════════════
pres.writeFile({ fileName: "D:\\Dashboard_FF\\HORIZON_Presentation.pptx" })
  .then(() => console.log("✅  HORIZON_Presentation.pptx written"))
  .catch(e => { console.error(e); process.exit(1); });
