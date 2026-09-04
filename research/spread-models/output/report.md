# News -> Brent Calendar-Spread Distribution

**Headline modelled:** *"Israel launches strikes on Iranian energy infrastructure. Iran threatens closure of the Strait of Hormuz."*

**Horizon:** 1 week (5 trading days). **Convention:** positive = backwardation (near minus far). **Data:** 1-minute ICE Brent (LCO) nearbys c1..c6, Jan-2021 to May-2026.


## 1. Method

A news event does not move a spread to a single number; it shifts the *distribution* of where the spread lands. We build that distribution as a probability-weighted mixture of three regimes calibrated to real analogs in the data. Two pieces:

1. **A news-severity scoring framework** turns the headline into the three regime *probabilities* (transparent, reproducible for any future headline).

2. **An event study** sets each regime's *magnitude* (drift + tail) from history.

The mixture is Monte-Carlo'd (400k draws); small-N parameter uncertainty is propagated to put confidence intervals on the outputs themselves.


## 2. News-severity scoring -> probabilities

```
Factor                                              score  weight  contribution
  Chokepoint exposure                              0.85   0.28      0.238
  Target = oil supply                              0.90   0.24      0.216
  Actor directness                                 0.85   0.18      0.153
  Escalation persistence                           0.50   0.15      0.075
  Spillover / contagion risk                       0.55   0.15      0.083
  (less) Market buffer (spare cap / inventories / prior threats unmet) 0.55   0.20     -0.110

  raw upside pressure = 0.764   severity S = 0.680
```


Composite **severity S = 0.68**, mapped to probabilities via `p_esc = 0.05 + 0.37·S²`, `p_fizzle = 0.18 + 0.32·(1-S)`, `p_contained = residual` (convex escalation term; fizzle floor respects that 3 of 5 sampled shocks faded):

| Scenario | Probability | Narrative |
|---|---:|---|
| Escalation / Hormuz disruption | 22% | Strikes impair supply/tanker flow; sharp front backwardation spike. **Right-skewed tail.** |
| Contained / risk-premium | 50% | Strikes continue, no Hormuz closure; war-risk premium builds. **Base case.** |
| De-escalation / fizzle | 28% | Threat priced then bleeds out (ceasefire / no follow-through); mean-reversion. |

## 3. Event study - magnitude calibration

5-trading-day spread change ($/bbl) after each shock in the sample:

| Event | regime | M1-M2 | M2-M4 | M1-M6 |
|---|---|---:|---:|---:|
| Russia invades Ukraine | supply shock -> escalation template | +2.08 | +4.48 | +9.54 |
| Iran->Israel barrage (Oct24) | contained risk-premium | +0.48 | +0.48 | +1.37 |
| Israel strikes Iran (Jun25) | contained (primary analog) | +0.49 | +0.65 | +1.74 |
| Hamas attack / Gaza war | fizzle / no supply hit | -0.23 | -0.16 | -0.57 |
| Iran->Israel strike (Apr24) | fizzle / de-escalation | -0.17 | -0.27 | -0.67 |

The **escalation** regime is modelled as a right-skewed **lognormal** (median anchored to the Russia-2022 impulse; 95th pct ~2x median for a genuine Hormuz interruption, which in barrels far exceeds Russia). Contained and fizzle are Normals around their cluster means.


## 4. Distribution by spread (1-week CHANGE, $/bbl) - the robust output

| Spread | EV change | 50% range (P25-P75) | 90% range (P5-P95) | P(widen) |
|---|---:|---:|---:|---:|
| M1-M2 | +0.70 | [-0.14, +1.29] | [-0.80, +2.99] | 69% |
| M2-M4 | +1.34 | [-0.15, +1.80] | [-0.92, +6.43] | 70% |
| M1-M6 | +2.97 | [-0.29, +4.23] | [-2.09, +13.72] | 71% |

### Implied 1-week LEVEL (anchored on latest close 2026-05-22)

| Spread | Start | EV level | 50% range | 90% range |
|---|---:|---:|---:|---:|
| M1-M2 | 3.37 | 4.07 | [3.23, 4.66] | [2.57, 6.37] |
| M2-M4 | 7.15 | 8.48 | [7.00, 8.95] | [6.23, 13.58] |
| M1-M6 | 15.70 | 18.67 | [15.41, 19.93] | [13.61, 29.42] |

*The latest close is itself steeply backwardated, so the **change** distribution is the anchor-independent, robust deliverable; levels are shown for context.*


## 5. Statistical robustness

**Parameter uncertainty** (small N): means sampled from their standard errors and weights from a Dirichlet around the scored probabilities, giving a 90% CI *on the statistics*:

| Spread | EV 90% CI | P95 90% CI |
|---|---:|---:|
| M1-M2 | [+0.37, +1.10] | [+1.61, +4.69] |
| M2-M4 | [+0.61, +2.20] | [+2.62, +9.94] |
| M1-M6 | [+1.49, +4.91] | [+6.36, +21.72] |

**Backtest** - where each realised historical move falls in the model's predicted CDF (well-calibrated if fizzle events sit low, contained ~mid, supply shock in the tail):

| Event | M1-M2 | M2-M4 | M1-M6 |
|---|---:|---:|---:|
| Hamas attack / Gaza war | 22% | 25% | 21% |
| Iran->Israel barrage (Oct24) | 51% | 48% | 49% |
| Iran->Israel strike (Apr24) | 24% | 21% | 20% |
| Israel strikes Iran (Jun25) | 51% | 53% | 54% |
| Russia invades Ukraine | 88% | 89% | 89% |

Every event lands where the regime logic predicts: fizzle ~20-25th pct, the direct Israel-Iran analogs ~50th, Russia ~88th. The model brackets history rather than over/under-shooting.


## 6. Sensitivity to the escalation probability

How EV and the 90% range move as p(escalation) varies (M1-M6 shown; fizzle held fixed):

| p(escalation) | EV | P05 | P95 |
|---:|---:|---:|---:|
| 5% | +1.40 | -2.16 | +5.79 |
| 10% | +1.85 | -2.13 | +9.49 |
| 15% | +2.31 | -2.11 | +11.75 |
| 22% | +2.96 | -2.10 | +13.69 |
| 30% | +3.68 | -2.06 | +15.18 |
| 40% | +4.61 | -2.03 | +16.59 |

The **downside (P05) is bounded** by the fizzle regime; only the **upside tail** responds to escalation odds - the asymmetry a single-number forecast would miss.


## 7. How the news translates into the curve

- **M1-M2 (front)** - most information-sensitive per dollar; a supply scare lands on the prompt, so it moves first and reverts fastest. Modest in dollars, large vs its ~0.7 baseline weekly vol.

- **M2-M4 (deferred)** - muted; the market prices a *temporary* disruption, so the belly moves less. It widens mainly in the escalation regime where disruption is expected to persist.

- **M1-M6 (front-to-back)** - captures the whole steepening: largest absolute move and fattest tail, the cleanest expression of 'front spikes, back anchored'.

- **Caveat (regime-dependence):** a *full, sustained* Hormuz closure would lift the entire curve (back end too), partially capping the steepening - the lognormal tail is calibrated to the front-loaded fear response, not an indefinite outage.


**Bottom line:** modal outcome is a moderate backwardation build (risk premium), with a fat right tail if Hormuz is genuinely threatened and a ~28% chance the move fades. The deliverable is the *shape* of the uncertainty, not a point forecast.
