"""Deck-ready PNG figures for the STRUCTURAL driver model -> output/figs/ (struct_*.png)."""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from load_spreads import load_daily_spreads
from event_study import event_response, EVENTS
from scoring import severity, scenario_probabilities_6
from structural_model import (SCENARIOS, SCEN_NAMES, SPREADS, simulate, summarize,
                              cross_validate_curve, driver_sensitivity, _event_table,
                              latest_levels, sensitivity_to_escalation,
                              KAPPA, A24, B24, A16, B16, BUFFER_MEAN)

NAVY = "#1E2761"; AMBER = "#E8A33D"; RED = "#C0392B"; TEAL = "#1C7293"
GREY = "#8892B0"; ICE = "#CADCFC"; ORANGE2 = "#D67D2C"
SPREAD_COLORS = {"M1-M2": NAVY, "M2-M4": TEAL, "M1-M6": AMBER}
SCEN_COLORS = [TEAL, NAVY, AMBER, ORANGE2, RED]

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

    # 1. history -------------------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for col in SPREADS:
        ax.plot(s.index, s[col], lw=0.9, color=SPREAD_COLORS[col], label=col)
    for d in EVENTS.values():
        ax.axvline(pd.Timestamp(d), color=RED, ls="--", lw=0.8, alpha=0.55)
    ax.axhline(0, color="#444", lw=0.6)
    ax.set_title("Brent calendar spreads, 2021-2026  (red = geopolitical shocks)")
    ax.set_ylabel("$/bbl   (positive = backwardation)")
    ax.legend(loc="upper left", frameon=False)
    save(fig, "struct_01_history.png")

    # 2. event study ---------------------------------------------------------
    resp = event_response(s)
    ev = pd.DataFrame({k: v["chg_5d"] for k, v in resp.items()}).T[SPREADS]
    short = {"Russia invades Ukraine": "Russia\n2022", "Hamas attack / Gaza war": "Hamas\n2023",
             "Iran->Israel strike (Apr24)": "Iran->Isr\nApr24",
             "Iran->Israel barrage (Oct24)": "Iran->Isr\nOct24",
             "Israel strikes Iran (Jun25)": "Isr->Iran\nJun25"}
    ev.index = [short[i] for i in ev.index]
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ev.plot(kind="bar", ax=ax, color=[SPREAD_COLORS[c] for c in SPREADS], width=0.78)
    ax.axhline(0, color="#444", lw=0.7)
    ax.set_title("Event study: 5-day Brent spread change after each shock ($/bbl)")
    ax.set_xticklabels(ev.index, rotation=0)
    ax.legend(frameon=False)
    save(fig, "struct_02_eventstudy.png")

    # 3. response function (the engine) -------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(12.4, 4.3))
    supply = np.linspace(0, 6, 200)
    for access, lab, c in [(1.0, "buffer fully accessible", TEAL),
                           (0.3, "buffer 30% accessible (Hormuz)", RED)]:
        cov = np.clip(BUFFER_MEAN * access / np.maximum(supply, 1e-6), 0, 1)
        E = supply * (1 - KAPPA * cov)
        axes[0].plot(supply, E, lw=2.4, color=c, label=lab)
    axes[0].plot(supply, supply, "k--", lw=0.9, alpha=0.5, label="no buffer (E = supply)")
    axes[0].set_xlabel("supply at risk (mb/d)")
    axes[0].set_ylabel("effective unmet shortfall E (mb/d)")
    axes[0].set_title("(a) Spare capacity helps only if shippable", fontsize=12.5)
    axes[0].legend(fontsize=10, frameon=False)
    rho = np.linspace(0, 1, 100)
    axes[1].plot(rho, A24 + B24 * rho, lw=2.4, color=TEAL, label="M2-M4 / M1-M2")
    axes[1].plot(rho, A16 + B16 * rho, lw=2.4, color=AMBER, label="M1-M6 / M1-M2")
    axes[1].set_xlabel("persistence  rho")
    axes[1].set_ylabel("deferred-month multiple")
    axes[1].set_title("(b) The curve fans wider with persistence", fontsize=12.5)
    axes[1].legend(fontsize=10, frameon=False)
    fig.tight_layout(w_pad=4)
    save(fig, "struct_03_response.png")

    # 4. scoring -> 5 scenario probabilities (2-panel: factor breakdown + scenarios)
    from scoring import FACTORS, severity as _sev
    S = severity()["severity"]
    sv = _sev()
    probs = scenario_probabilities_6()
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.5))

    # left: factor contribution horizontal bars
    names = [f.name for f in FACTORS]
    contribs = [sv["contributions"][f.name] for f in FACTORS]
    colors_f = [TEAL, NAVY, AMBER, ORANGE2, RED]
    bars = axes[0].barh(names[::-1], contribs[::-1], color=colors_f[::-1], height=0.55)
    for bar, val in zip(bars, contribs[::-1]):
        axes[0].text(val + 0.002, bar.get_y() + bar.get_height()/2,
                     f"{val:.3f}", va="center", fontsize=10.5, fontweight="bold")
    axes[0].axvline(0, color="#444", lw=0.8)
    axes[0].set_xlabel("weighted contribution to S")
    axes[0].set_title(f"(a) Factor contributions  →  S = {S:.2f}", fontsize=12.5)
    axes[0].set_xlim(0, max(contribs) * 1.35)

    # right: 5 scenario probabilities
    axes[1].bar(range(len(probs)), list(probs.values()), color=SCEN_COLORS, width=0.6)
    axes[1].set_xticks(range(len(probs)))
    axes[1].set_xticklabels(list(probs.keys()), rotation=16, ha="right", fontsize=9.5)
    for i, v in enumerate(probs.values()):
        axes[1].text(i, v + 0.006, f"{v:.1%}", ha="center", fontsize=11, fontweight="bold")
    axes[1].set_ylabel("probability")
    axes[1].set_ylim(0, max(probs.values()) * 1.2)
    axes[1].set_title(f"(b) S = {S:.2f}  →  five structural scenarios", fontsize=12.5)

    fig.tight_layout(w_pad=3)
    save(fig, "struct_04_scoring.png")

    # simulate once for the next figures ------------------------------------
    out, comp, pvec = simulate(n=400_000, seed=42)
    table, scen = summarize(out, comp, pvec)

    # 5. distributions -------------------------------------------------------
    # NOTE: the closure tail pushes the 99th pct far to the right (M1-M6 ~ +60),
    # which crushes the visible body. Clip the x-axis at the 97th pct and bin over
    # that window so the modal mass and the 50% / 90% bands are actually legible;
    # the far tail is conveyed by the title's 90% range and the scenario chart.
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, sp in zip(axes, SPREADS):
        d = out[sp]
        p5, p25, p75, p95 = np.percentile(d, [5, 25, 75, 95])
        xlo = min(np.percentile(d, 1.0), -0.5)
        xhi = np.percentile(d, 97.0)
        ax.hist(d, bins=110, range=(xlo, xhi), color=ICE)
        ax.axvspan(p5, p95, color=AMBER, alpha=0.12)
        ax.axvspan(p25, p75, color=AMBER, alpha=0.30)
        ax.axvline(d.mean(), color=RED, lw=2)
        ax.axvline(0, color="#444", lw=0.7)
        ax.set_xlim(xlo, xhi)
        ax.set_yticks([])
        ax.set_title(f"{sp}\nEV {d.mean():+.2f}   90% [{p5:+.1f}, {p95:+.1f}]")
        ax.set_xlabel("1-week change ($/bbl)")
    fig.suptitle("Structural Monte Carlo: 1-week spread-change distribution  "
                 "(red = EV, bands = 50% / 90%;  x-axis clipped at 97th pct — closure tail extends further)",
                 fontweight="bold", y=1.03, fontsize=13)
    save(fig, "struct_05_distributions.png")

    # 6. per-scenario expected change ---------------------------------------
    fig, ax = plt.subplots(figsize=(10, 4.3))
    scen[SPREADS].plot(kind="bar", ax=ax, color=[SPREAD_COLORS[c] for c in SPREADS], width=0.78)
    ax.axhline(0, color="#444", lw=0.7)
    ax.set_title("Expected 1-week spread change by scenario ($/bbl)")
    ax.set_xticklabels(scen.index, rotation=14, ha="right", fontsize=10)
    ax.legend(frameon=False)
    save(fig, "struct_06_scenarios.png")

    # 7. validation: LOO vs naive -------------------------------------------
    loo, st = cross_validate_curve(s)
    df = _event_table(s)
    loo = loo.merge(df[["event"]], on="event")
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    lo, hi = loo["M1-M6 actual"].min() - 1, loo["M1-M6 actual"].max() + 1
    ax.plot([lo, hi], [lo, hi], "k--", lw=0.9, alpha=0.6, label="perfect")
    ax.scatter(loo["M1-M6 actual"], loo["naive-pred"], s=90, color=RED, alpha=0.7,
               label=f"naive mean-ratio (RMSE {st['rmse_naive_ratio']:.2f})")
    ax.scatter(loo["M1-M6 actual"], loo["M1-M6 LOO-pred"], s=110, color=NAVY, zorder=3,
               label=f"LOO curve law (RMSE {st['rmse_LOO_curve']:.2f})")
    ax.set_xlabel("M1-M6 actual ($/bbl)")
    ax.set_ylabel("predicted ($/bbl)")
    ax.set_title("Out-of-sample test: leave-one-out\n(curve law vs naive baseline)")
    ax.legend(fontsize=10, frameon=False, loc="upper left")
    save(fig, "struct_07_validation.png")

    # 8. driver tornado on M1-M6 --------------------------------------------
    base, tor = driver_sensitivity(target="M1-M6")
    fig, ax = plt.subplots(figsize=(9, 4.0))
    y = np.arange(len(tor))
    ax.barh(y, tor["high"] - base, left=base, color=RED, alpha=0.85, label="driver at scenario high")
    ax.barh(y, tor["low"] - base, left=base, color=TEAL, alpha=0.85, label="driver at scenario low")
    ax.axvline(base, color="#222", lw=1.2)
    ax.set_yticks(y); ax.set_yticklabels(tor["driver"])
    ax.set_xlabel("M1-M6 1-week change ($/bbl)")
    ax.set_title(f"Driver tornado on M1-M6   (base = {base:.2f})")
    ax.legend(fontsize=10, frameon=False, loc="lower right")
    ax.invert_yaxis()
    save(fig, "struct_08_tornado.png")

    # 9. fan chart: today's level -> 1-week distribution ---------------------
    levels = latest_levels(s)
    fig, ax = plt.subplots(figsize=(9.5, 4.4))
    x = [0, 1]
    for sp in SPREADS:
        d = out[sp]; l0 = levels[sp]; c = SPREAD_COLORS[sp]
        p5, p25, ev_, p75, p95 = (l0 + np.percentile(d, 5), l0 + np.percentile(d, 25),
                                  l0 + d.mean(), l0 + np.percentile(d, 75),
                                  l0 + np.percentile(d, 95))
        ax.fill_between(x, [l0, p5], [l0, p95], color=c, alpha=0.10)
        ax.fill_between(x, [l0, p25], [l0, p75], color=c, alpha=0.25)
        ax.plot(x, [l0, ev_], color=c, marker="o", lw=2.2,
                label=f"{sp}:  {l0:.1f} -> {ev_:.1f}")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["today", "+1 week"])
    ax.set_ylabel("$/bbl   (positive = backwardation)")
    ax.set_title("Fan chart: spread level today -> 1-week distribution "
                 "(bands = 50% / 90%)")
    ax.legend(frameon=False, loc="upper left")
    save(fig, "struct_09_fan.png")

    # 10. sensitivity to escalation probability -----------------------------
    se = sensitivity_to_escalation()
    p_scored = sum(__import__("scoring").scenario_probabilities_6()[k]
                   for k in ["Hormuz harassment", "Iranian export infra destroyed",
                             "Hormuz closure (tail)"])
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.9))
    for ax, sp in zip(axes, SPREADS):
        d = se[se.spread == sp]
        ax.fill_between(d.p_escalation, d.p05, d.p95, color=AMBER, alpha=0.2, label="90% range")
        ax.plot(d.p_escalation, d.EV, color=RED, marker="o", lw=2, label="EV")
        ax.axvline(p_scored, color=NAVY, ls="--", lw=1.2, label="scored p")
        ax.axhline(0, color="#444", lw=0.6)
        ax.set_title(sp); ax.set_xlabel("p(escalation family)")
    axes[0].set_ylabel("1-week change ($/bbl)")
    axes[0].legend(fontsize=9, frameon=False, loc="upper left")
    fig.suptitle("Sensitivity to escalation probability  "
                 "(downside bounded, upside fans out)", fontweight="bold", y=1.04)
    save(fig, "struct_10_sensitivity.png")

    # 11. backtest: where does each realised shock fall in OUR distribution? ---
    # Complements the LOO test (which validates curve geometry). Here we ask the
    # distributional question: does the 1-week distribution this model produces
    # actually bracket the moves real shock weeks delivered? For each historical
    # event we locate its realised 5-day change as a percentile of our simulated draws.
    resp_chg = pd.DataFrame({k: v["chg_5d"] for k, v in resp.items()}).T[SPREADS]
    resp_chg.index = [short[i] for i in resp_chg.index]
    pct = pd.DataFrame(index=resp_chg.index, columns=SPREADS, dtype=float)
    for ev_name in resp_chg.index:
        for sp in SPREADS:
            pct.loc[ev_name, sp] = float((out[sp] < resp_chg.loc[ev_name, sp]).mean())
    # order rows calm -> severe by mean percentile for a readable gradient
    pct = pct.loc[pct.mean(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(7.6, 4.1))
    ax.imshow(pct.values.astype(float), cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(SPREADS))); ax.set_xticklabels(SPREADS)
    ax.set_yticks(range(len(pct.index)))
    ax.set_yticklabels([i.replace("\n", " ") for i in pct.index])
    for i in range(pct.shape[0]):
        for j in range(pct.shape[1]):
            ax.text(j, i, f"{pct.values[i, j]:.0%}", ha="center", va="center",
                    fontsize=11, fontweight="bold")
    ax.set_title("Backtest: where each realised shock falls in our distribution\n"
                 "(percentile of the simulated 1-week change)", fontsize=12.5)
    save(fig, "struct_11_backtest.png")


if __name__ == "__main__":
    main()
