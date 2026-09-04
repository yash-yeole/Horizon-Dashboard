# Scoring report — EIA crude release, 24 June 2026

**Question:** did the market do what we predicted, and if so why — if not, why not?

## Data used
- `bars_1min_20260624.db` (provided): 1-minute OHLCV for WTI (`CL_*`) and Brent
  (`CO_*`) futures by contract month, 13:15–19:35 **London time**.
- Front contracts on the day: WTI `CL_Q26` (~$70.3), Brent `CO_Q26` (~$73.9).
- Release timestamp: **15:30 London = 10:30 ET** (confirmed by the volume/vol
  signature and the file ending at Brent's 19:30 London settle).
- **Not in this data:** RBOB / heating-oil — so the product-crack call can't be
  scored here; only WTI flat, Brent, WTI–Brent and the WTI front timespread can.

## What we predicted (ex-ante)
| Deliverable | Our call |
|---|---|
| The number | **−4.9 M bbl draw** (vs −3.9 consensus) — bigger draw than the street |
| Direction | **NEUTRAL, slight bullish tilt** (bigger-than-consensus draw) |
| Magnitude | small — inventory is a **secondary** WTI driver this regime |
| Spreads | WTI flat ~neutral; US-draw firms **WTI vs Brent**; backwardation steepens |
| Top-3 factors | dollar/macro > geopolitical news > the inventory surprise |

## What actually happened
- **The number:** actual **−6.088 M bbl** (an even bigger draw). Our −4.9 was
  closer to the print than the −3.9 consensus (error 1.2 vs 2.2 M bbl) — **we beat
  the street**, and called the direction of the surprise (bullish) correctly.
- **WTI reaction (from 15:30):** +0.30% (5m) → +0.67% (30m) → **+0.85% (60m)**,
  peaking **+1.14% at 16:40**, then fading to +0.40% (2h) and **−0.06% by the
  19:35 settle** — a clean round-trip back to flat.
- **Pre-release:** WTI had drifted **−0.68%** into the print (soft macro tape).
- **Brent:** moved nearly in lockstep (+0.76% at 60m).
- **WTI–Brent spread:** narrowed modestly, −3.63 → −3.49 (WTI a touch firmer).
- **WTI front timespread (Q26–U26):** steepened +0.39 → +0.45 at 60m (front-end
  firmed on the draw), back to +0.40 at 2h.

## Did it match? — scorecard
| Dimension | Predicted | Actual | Verdict |
|---|---|---|---|
| The number | −4.9 (vs −3.9 cons.) | −6.088 | ✅ right direction, beat consensus |
| Reaction direction | slight bullish | +0.85% pop | ✅ correct |
| Net / magnitude | NEUTRAL (secondary driver) | pop **faded to flat** by settle | ✅ textbook confirmation |
| WTI vs Brent | WTI firmer (US draw) | spread −3.63→−3.49 | ✅ small, right way |
| Backwardation | steepens | +0.39→+0.45 | ✅ small, right way |

## Was this what we expected? — yes, on every scorable dimension

The release behaved **exactly** as the framework said it would:
1. **A bigger-than-expected draw produced a bullish kick** — WTI rallied ~0.85% in
   the hour after the print. Our surprise sign was right.
2. **But the kick was transient.** The inventory impulse round-tripped to flat by
   settlement. The print did **not** set the day's direction — precisely the
   "secondary driver, NEUTRAL net" thesis. The soft tape that had WTI down −0.68%
   pre-release reasserted itself and reabsorbed the bounce.

This is the 7-year finding observed live in one event: **inventories give a
short-lived intraday move, the dollar/geopolitical regime owns the close.**

## The reasons we considered — and how they held up
- **Supply/demand balance model → bigger draw than consensus.** Held: the tight
  lagged balance (−16.7 M bbl) pointed to a large draw; actual was even larger.
- **Regime-conditional reaction → secondary driver.** Held: the bullish surprise
  moved price ~1% intraday then faded — no lasting directional impact.
- **US-specific barrel → WTI firms vs Brent, backwardation steepens.** Held
  directionally, but **small**.

## Honest caveats
- **Brent moved almost as much as WTI** (+0.76% vs +0.85%). A purely US-crude story
  would show WTI outperforming Brent more clearly; the near-lockstep move says the
  pop was a **broad crude-complex / short-covering reaction to the headline draw**,
  not a clean US-only repricing. The WTI–Brent spread did narrow slightly (our
  lean), but the effect was minor.
- **Products not scored** — RBOB/HO aren't in this DB, so the "cracks are the most
  inventory-sensitive vehicle" call is untested here. Worth pulling product tick
  data to score that channel.
- **One event** — a single release confirms the *mechanism* (pop-and-fade,
  secondary driver); it isn't statistical proof.

## Bottom line
**Correct call.** We predicted a bigger-than-consensus draw (and beat the street on
the number), a mild bullish kick, and a NEUTRAL net because inventories are a
secondary driver. The tape delivered exactly that: a ~1% bullish pop on the −6.09
print that fully faded to a flat settle. The framework's central claim — *the EIA
crude number moves WTI intraday but the dollar and geopolitics own the day* — is
borne out tick-by-tick.
