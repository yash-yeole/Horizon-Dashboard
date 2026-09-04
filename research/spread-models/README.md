# News -> Brent Calendar-Spread Distribution

Framework that converts an energy-market news event into a probability distribution for
Brent (ICE LCO) calendar spreads (M1-M2, M2-M4, M1-M6) over a 1-week horizon.

Modelled headline: *"Israel launches strikes on Iranian energy infrastructure. Iran
threatens closure of the Strait of Hormuz."*

## Pipeline

| Script | Role |
|---|---|
| `load_spreads.py` | Parse `../data/LCO_data.csv` (1-min, c1..c6), resample to daily, build the three spreads (positive = backwardation). |
| `event_study.py` | Baseline 5-day change distribution + geopolitical event study (Russia-2022, Gaza-2023, Iran-Israel Apr/Oct-2024, Jun-2025). |
| `scoring.py` | **News-severity scoring framework** - decomposes the headline into oil-relevant factors and *derives* the three regime probabilities (reproducible for any headline). |
| `mixture_model.py` | 3-regime mixture (right-skewed lognormal escalation + Normal contained/fizzle), 400k-draw Monte Carlo, **parameter-uncertainty CIs**, **backtest**, **sensitivity** -> `output/results.json`. |
| `report.py` | Renders the written deliverable -> `output/report.md`. |
| `news_to_spread_distribution.ipynb` | Executable notebook with all plots (build via `build_notebook.py`). |

## Run

```
cd analysis
python report.py        # full analysis + writes output/report.md and results.json
```

`python event_study.py` and `python mixture_model.py` print intermediate diagnostics.

## Method

The output is not a point forecast but a distribution: a probability-weighted mixture of
three regimes, each calibrated to real analogs in five years of Brent data. The baseline
sets the natural width of a normal week; the event study sets the drift and the fat tail.
Tune `SCENARIO_PROB` in `mixture_model.py` to stress different escalation odds.
