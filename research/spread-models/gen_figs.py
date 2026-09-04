"""Generate deck-ready PNG figures into output/figs/. Reuses the analysis modules."""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

from load_spreads import load_daily_spreads
from event_study import event_response, EVENTS, baseline_stats
from scoring import severity, FACTORS, BUFFER
from mixture_model import (calibrate, simulate, summarize, SPREADS, SEED, SCENARIO_PROB,
                           validate_against_history, sensitivity_to_escalation)

# palette ---------------------------------------------------------------------
NAVY   = "#1E2761"
AMBER  = "#E8A33D"
RED    = "#C0392B"
TEAL   = "#1C7293"
GREY   = "#8892B0"
ICE    = "#CADCFC"
SPREAD_COLORS = {"M1-M2": NAVY, "M2-M4": TEAL, "M1-M6": AMBER}

plt.rcParams.update({
    "figure.facecolor": "white", "axes.facecolor": "white",
    "axes.edgecolor": "#cccccc", "axes.grid": True, "grid.alpha": 0.25,
    "axes.titleweight": "bold", "font.size": 12, "axes.titlesize": 14,
    "axes.spines.top": False, "axes.spines.right": False,
})

FIGD = os.path.join(os.path.dirname(__file__), "output", "figs")
os.makedirs(FIGD, exist_ok=True)


def save(fig, name):
    fig.savefig(os.path.join(FIGD, name), dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote", name)


def main():
    s = load_daily_spreads()
    params = calibrate(s)
    rng = np.random.default_rng(SEED)
    draws, comp, names = simulate(params, rng)
    table, scen, levels0 = summarize(s, params, draws, comp, names)

    # 1. spread history with event markers ------------------------------------
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for col in SPREADS:
        ax.plot(s.index, s[col], lw=0.9, color=SPREAD_COLORS[col], label=col)
    for d in EVENTS.values():
        ax.axvline(pd.Timestamp(d), color=RED, ls="--", lw=0.8, alpha=0.55)
    ax.axhline(0, color="#444", lw=0.6)
    ax.set_title("Brent calendar spreads, 2021-2026  (red = geopolitical shocks)")
    ax.set_ylabel("$/bbl   (positive = backwardation)")
    ax.legend(loc="upper left", frameon=False)
    save(fig, "01_history.png")

    # 2. event study bars ------------------------------------------------------
    resp = event_response(s)
    ev = pd.DataFrame({k: v["chg_5d"] for k, v in resp.items()}).T[SPREADS]
    short = {"Russia invades Ukraine": "Russia\n2022", "Hamas attack / Gaza war": "Hamas\n2023",
             "Iran->Israel strike (Apr24)": "Iran→Isr\nApr24",
             "Iran->Israel barrage (Oct24)": "Iran→Isr\nOct24",
             "Israel strikes Iran (Jun25)": "Isr→Iran\nJun25"}
    ev.index = [short[i] for i in ev.index]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ev.plot(kind="bar", ax=ax, color=[SPREAD_COLORS[c] for c in SPREADS], width=0.78)
    ax.axhline(0, color="#444", lw=0.7)
    ax.set_title("Event study: 5-day Brent spread change after each shock ($/bbl)")
    ax.set_xticklabels(ev.index, rotation=0)
    ax.legend(frameon=False)
    save(fig, "02_eventstudy.png")

    # 3. scoring: factor contributions + S->prob map --------------------------
    S = severity()["severity"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    wsum = sum(f.weight for f in FACTORS)
    contribs = {f.name: f.score * f.weight / wsum for f in FACTORS}
    contribs["Market buffer (−)"] = -BUFFER.weight * BUFFER.score
    keys = list(contribs)[::-1]
    vals = [contribs[k] for k in keys]
    axes[0].barh(keys, vals, color=[TEAL if v > 0 else RED for v in vals])
    axes[0].axvline(0, color="#444", lw=0.7)
    axes[0].set_title(f"Severity factors  →  S = {S:.2f}")
    Sg = np.linspace(0, 1, 100)
    pe = 0.05 + 0.37 * Sg**2; pf = 0.18 + 0.32 * (1 - Sg); pc = 1 - pe - pf
    axes[1].plot(Sg, pe, color=RED, lw=2, label="escalation")
    axes[1].plot(Sg, pc, color=NAVY, lw=2, label="contained")
    axes[1].plot(Sg, pf, color=AMBER, lw=2, label="fizzle")
    axes[1].axvline(S, color="#444", ls="--", lw=1)
    axes[1].set_xlabel("severity S"); axes[1].set_ylabel("probability")
    axes[1].set_title("Scoring map: S → regime probabilities")
    axes[1].legend(frameon=False)
    save(fig, "03_scoring.png")

    # 4. distribution histograms with bands -----------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, sp in zip(axes, SPREADS):
        d = draws[sp]
        p5, p25, p75, p95 = np.percentile(d, [5, 25, 75, 95])
        ax.hist(d, bins=160, color=ICE)
        ax.axvspan(p5, p95, color=AMBER, alpha=0.12)
        ax.axvspan(p25, p75, color=AMBER, alpha=0.30)
        ax.axvline(d.mean(), color=RED, lw=2)
        ax.axvline(0, color="#444", lw=0.7)
        ax.set_xlim(np.percentile(d, 0.3), np.percentile(d, 99.3))
        ax.set_yticks([])
        ax.set_title(f"{sp}\nEV {d.mean():+.2f}   90% [{p5:+.1f}, {p95:+.1f}]")
        ax.set_xlabel("1-week change ($/bbl)")
    fig.suptitle("Distribution of the 1-week spread change (red = EV, bands = 50% / 90%)",
                 fontweight="bold", y=1.03)
    save(fig, "04_distributions.png")

    # 5. fan chart -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 4.2))
    x = [0, 1]
    for sp in SPREADS:
        d = draws[sp]; l0 = levels0[sp]; c = SPREAD_COLORS[sp]
        p5, p25, ev_, p75, p95 = (l0 + np.percentile(d, 5), l0 + np.percentile(d, 25),
                                  l0 + d.mean(), l0 + np.percentile(d, 75), l0 + np.percentile(d, 95))
        ax.fill_between(x, [l0, p5], [l0, p95], color=c, alpha=0.10)
        ax.fill_between(x, [l0, p25], [l0, p75], color=c, alpha=0.25)
        ax.plot(x, [l0, ev_], color=c, marker="o", lw=2, label=f"{sp}: {l0:.1f}→{ev_:.1f}")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["today", "+1 week"])
    ax.set_title("Fan chart: spread level today → 1-week distribution")
    ax.set_ylabel("$/bbl"); ax.legend(frameon=False)
    save(fig, "05_fan.png")

    # 6. backtest heatmap ------------------------------------------------------
    val = validate_against_history(s).pivot(index="event", columns="spread", values="model_pctile")[SPREADS]
    val.index = [short[i] for i in val.index]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    im = ax.imshow(val.values, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(SPREADS))); ax.set_xticklabels(SPREADS)
    ax.set_yticks(range(len(val.index))); ax.set_yticklabels([i.replace("\n", " ") for i in val.index])
    for i in range(val.shape[0]):
        for j in range(val.shape[1]):
            ax.text(j, i, f"{val.values[i,j]:.0%}", ha="center", va="center", fontsize=11)
    ax.set_title("Backtest: model percentile of each realised move")
    save(fig, "06_backtest.png")

    # 7. sensitivity fans ------------------------------------------------------
    se = sensitivity_to_escalation(s)
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, sp in zip(axes, SPREADS):
        d = se[se.spread == sp]
        ax.fill_between(d.p_escalation, d.p05, d.p95, color=AMBER, alpha=0.2)
        ax.plot(d.p_escalation, d.EV, color=RED, marker="o", lw=2)
        ax.axvline(SCENARIO_PROB["Escalation / Hormuz disruption"], color=NAVY, ls="--", lw=1)
        ax.axhline(0, color="#444", lw=0.6)
        ax.set_title(sp); ax.set_xlabel("p(escalation)")
    axes[0].set_ylabel("1-week change ($/bbl)")
    fig.suptitle("Sensitivity to escalation probability (dashed = scored 22%)",
                 fontweight="bold", y=1.04)
    save(fig, "07_sensitivity.png")


if __name__ == "__main__":
    main()
