import { useEffect, useMemo, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, ReferenceArea, AreaChart, Area,
} from 'recharts';
import { RefreshCw } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button, Tabs, StatusDot, Skeleton } from '@/components/ui';
import { ChartTooltip } from '@/components/charts/ChartTooltip';
import { usePaperState, usePaperBacktest } from '@/hooks/usePaper';
import { cn } from '@/lib/utils';
import type { PaperState, PaperStructure, PaperTrade, BacktestResult, BacktestTrade } from '@/types/paper';

const ORDER = ['wti_cal', 'wti_c2c3', 'wti_fly', 'brent_cal', 'brent_c2c3', 'brent_fly', 'wti_brent'];

// WTI (CL) and Brent (CO) futures are 1,000 bbl/contract — converts $/bbl spread PnL to $.
const CONTRACT_BBL = 1000;

const axisProps = {
  tick: { fill: '#475569', fontSize: 10 },
  axisLine: { stroke: '#1f2230' },
  tickLine: false,
};

function num(v: number | null | undefined, d = 3): string {
  return v == null || Number.isNaN(v) ? '—' : v.toFixed(d);
}

function money(v: number): string {
  const sign = v < 0 ? '-' : '';
  return `${sign}$${Math.abs(v).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function hhmm(iso: string): string {
  const t = new Date(iso);
  return `${String(t.getMonth() + 1).padStart(2, '0')}/${String(t.getDate()).padStart(2, '0')} ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
}

function RichCheapBadge({ value }: { value?: string }) {
  const map: Record<string, string> = {
    RICH: 'bg-red-500/15 text-red-400',
    CHEAP: 'bg-green-500/15 text-green-400',
    FAIR: 'bg-slate-500/15 text-slate-400',
    UNKNOWN: 'bg-slate-500/15 text-slate-500',
  };
  const cls = map[value ?? 'UNKNOWN'] ?? map.UNKNOWN;
  return <span className={cn('rounded px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider', cls)}>{value ?? '—'}</span>;
}

function WatchOnlyBadge() {
  return (
    <span className="rounded px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider bg-amber-500/15 text-amber-400">
      Watch only
    </span>
  );
}

function EngineBadge({ engine, lookback }: { engine?: string; lookback?: number | null }) {
  if (!engine) return null;
  const rolling = engine === 'rolling';
  const cls = rolling ? 'bg-sky-500/15 text-sky-400' : 'bg-violet-500/15 text-violet-400';
  const txt = rolling ? `Rolling z${lookback ? ` · ${lookback}` : ''}` : 'Model z';
  return <span className={cn('rounded px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider', cls)}>{txt}</span>;
}

function ActionBadge({ action }: { action?: string }) {
  const buy = action === 'BUY';
  const sell = action === 'SELL';
  const cls = buy ? 'bg-green-500/15 text-green-400' : sell ? 'bg-red-500/15 text-red-400' : 'bg-slate-500/15 text-slate-400';
  return <span className={cn('rounded px-2 py-0.5 text-[11px] font-bold uppercase tracking-wider', cls)}>{action ?? 'NO TRADE'}</span>;
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-slate-500">{label}</p>
      <p className={cn('mono mt-0.5 text-lg font-semibold', accent ?? 'text-slate-100')}>{value}</p>
    </div>
  );
}

function FairPriceBlock({ s }: { s: PaperStructure }) {
  const z = s.live_z ?? null;
  const zAccent = z == null ? 'text-slate-100' : z > 0 ? 'text-red-400' : 'text-green-400';
  const rolling = s.engine === 'rolling';
  const hasDrift = s.fv_drift != null && s.fair_value_fundamental != null;
  return (
    <Card>
      <CardHeader
        title="Fair Price"
        subtitle={`${s.label}${s.legs ? ` · ${s.legs}` : ''}`}
        action={
          <div className="flex items-center gap-2">
            <EngineBadge engine={s.engine} lookback={s.roll_lookback} />
            {s.watch_only && <WatchOnlyBadge />}
            <RichCheapBadge value={s.rich_cheap} />
          </div>
        }
      />
      <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-4">
        <Metric label={rolling ? 'Roll Anchor' : 'Fair Value'} value={num(rolling ? s.roll_anchor : s.fair_value)} />
        <Metric label="Live Spread" value={num(s.live_spread)} />
        <Metric label="Live Z" value={num(z, 2)} accent={zAccent} />
        <Metric label={rolling ? 'Roll σ' : 'Resid σ'} value={num(rolling ? s.roll_std : s.resid_std)} />
      </div>
      {rolling ? (
        <div className="flex flex-wrap items-center gap-x-2 border-t border-[#1f2230] px-4 py-2 text-[11px] text-slate-400">
          <span className="text-slate-500">Anchor =</span>
          <span className="mono text-slate-200">{num(s.roll_anchor)}</span>
          <span className="text-slate-500">rolling mean of last {s.roll_lookback} bars · z vs σ</span>
          <span className="mono text-slate-300">{num(s.roll_std)}</span>
          <span className="ml-auto text-slate-600">model overlay: fair value <span className="mono text-slate-400">{num(s.fair_value)}</span></span>
        </div>
      ) : hasDrift && (
        <div className="flex flex-wrap items-center gap-x-2 border-t border-[#1f2230] px-4 py-2 text-[11px] text-slate-400">
          <span className="text-slate-500">Fair value =</span>
          <span className="mono text-slate-200">{num(s.fair_value_fundamental)}</span>
          <span className="text-slate-500">fundamental anchor</span>
          <span className="text-slate-600">{(s.fv_drift ?? 0) >= 0 ? '+' : '−'}</span>
          <span className={cn('mono', (s.fv_drift ?? 0) >= 0 ? 'text-green-400' : 'text-red-400')}>{num(Math.abs(s.fv_drift ?? 0))}</span>
          <span className="text-slate-500">regime drift de-bias</span>
        </div>
      )}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 border-t border-[#1f2230] px-4 py-2.5 text-[11px] text-slate-400">
        <span>Regime <span className="mono text-slate-200">{s.regime ?? '—'}</span></span>
        <span>Confidence <span className="mono text-slate-200">{s.confidence ?? '—'}</span></span>
        <span>Bars <span className="mono text-slate-200">{s.bars ?? 0}</span></span>
        {s.ood && <span className="text-amber-400">OOD</span>}
        {s.near_boundary && <span className="text-amber-400">Near boundary</span>}
        <span className="ml-auto text-slate-500">as of {s.as_of ? hhmm(s.as_of) : '—'}</span>
      </div>
    </Card>
  );
}

function SignalPanel({ s }: { s: PaperStructure }) {
  const sig = s.signal;
  return (
    <Card className="flex flex-col">
      <CardHeader
        title="Live Signal"
        action={
          <div className="flex items-center gap-2">
            {s.watch_only && <WatchOnlyBadge />}
            <ActionBadge action={sig?.action} />
          </div>
        }
      />
      <div className="flex-1 space-y-2 p-4 text-[12px]">
        {s.watch_only && (
          <p className="rounded bg-amber-500/10 px-2 py-1 text-[11px] leading-snug text-amber-400">
            Butterfly flagged unreliable by the model eval — signals shown but not actioned.
          </p>
        )}
        {sig ? (
          <>
            <Row k="Direction" v={sig.direction ?? '—'} />
            <Row k="Planned Entry" v={num(sig.planned_entry)} />
            <Row k="Target" v={num(sig.target)} />
            <Row k="Stop" v={num(sig.stop)} />
            {sig.rationale && <p className="pt-1 text-[11px] leading-snug text-slate-400">{sig.rationale}</p>}
          </>
        ) : (
          <p className="text-[11px] text-slate-500">No live context (insufficient bars or fair value).</p>
        )}
        {s.thresholds && (
          <div className="border-t border-[#1f2230] pt-2 text-[10px] text-slate-500">
            entry ±{s.thresholds.entry} · exit ±{s.thresholds.exit} · stop ±{s.thresholds.stop} · extreme ±{s.thresholds.z_extreme}
          </div>
        )}
      </div>
    </Card>
  );
}

function Row({ k, v, accent }: { k: string; v: string; accent?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-slate-500">{k}</span>
      <span className={cn('mono', accent ?? 'text-slate-200')}>{v}</span>
    </div>
  );
}

function OpenPositionCard({ s }: { s: PaperStructure }) {
  const p = s.open_position;
  if (!p) {
    return (
      <Card className="flex flex-col">
        <CardHeader title="Open Position" />
        <div className="flex flex-1 items-center justify-center p-4 text-[11px] text-slate-500">Flat — no open position</div>
      </Card>
    );
  }
  const pnlAccent = (p.unrealized_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400';
  return (
    <Card className="flex flex-col">
      <CardHeader
        title="Open Position"
        action={<span className={cn('rounded px-2 py-0.5 text-[11px] font-bold', p.direction === 'LONG' ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400')}>{p.direction}</span>}
      />
      <div className="flex-1 space-y-2 p-4 text-[12px]">
        <Row k="Entry" v={`${num(p.entry_price)} @ ${hhmm(p.entry_ts)}`} />
        <Row k="Current" v={num(p.current_price)} />
        <Row k="Current Z" v={num(p.current_z, 2)} />
        <Row k="Target / Stop" v={`${num(p.target)} / ${num(p.stop)}`} />
        <Row k="Unrealized PnL" v={num(p.unrealized_pnl)} accent={pnlAccent} />
        <Row k="Regime" v={p.regime ?? '—'} />
      </div>
    </Card>
  );
}

function ZScoreChart({ s }: { s: PaperStructure }) {
  const data = (s.z_series ?? []).filter((p) => p.z != null).map((p) => ({ t: hhmm(p.t), z: p.z as number }));
  const th = s.thresholds;
  return (
    <Card className="flex h-[320px] flex-col">
      <CardHeader title="Intraday Z-Score" subtitle="Deviation from daily fair value" />
      <div className="flex-1 p-2">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
              <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
              <XAxis dataKey="t" {...axisProps} minTickGap={40} />
              <YAxis {...axisProps} domain={['auto', 'auto']} width={40} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2d3e' }} />
              {th && (
                <>
                  <ReferenceArea y1={-th.entry} y2={th.entry} fill="#10b981" fillOpacity={0.04} />
                  <ReferenceLine y={0} stroke="#2a2d3e" />
                  <ReferenceLine y={th.entry} stroke="#f59e0b" strokeDasharray="4 3" />
                  <ReferenceLine y={-th.entry} stroke="#f59e0b" strokeDasharray="4 3" />
                  <ReferenceLine y={th.stop} stroke="#ef4444" strokeDasharray="2 3" />
                  <ReferenceLine y={-th.stop} stroke="#ef4444" strokeDasharray="2 3" />
                </>
              )}
              <Line type="monotone" dataKey="z" stroke="#3b82f6" strokeWidth={1.5} dot={false} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-[11px] text-slate-500">No z-series</div>
        )}
      </div>
    </Card>
  );
}

function EquityCurve({ s }: { s: PaperStructure }) {
  const data = (s.equity_curve ?? []).filter((p) => p.equity != null).map((p) => ({ t: hhmm(p.t), equity: p.equity as number }));
  return (
    <Card className="flex h-[320px] flex-col">
      <CardHeader title="Equity Curve" subtitle="Cumulative net PnL" />
      <div className="flex-1 p-2">
        {data.length ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
              <defs>
                <linearGradient id="eq-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
              <XAxis dataKey="t" {...axisProps} minTickGap={40} />
              <YAxis {...axisProps} domain={['auto', 'auto']} width={40} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2d3e' }} />
              <ReferenceLine y={0} stroke="#2a2d3e" />
              <Area type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={1.75} fill="url(#eq-grad)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-[11px] text-slate-500">No closed trades yet</div>
        )}
      </div>
    </Card>
  );
}

function TradeBlotter({ s }: { s: PaperStructure }) {
  const trades = s.trades ?? [];
  return (
    <Card className="flex flex-col">
      <CardHeader title="Trade Blotter" subtitle={`${trades.length} closed trade${trades.length === 1 ? '' : 's'}`} />
      <div className="overflow-x-auto">
        {trades.length ? (
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-[#1f2230] text-left text-slate-500">
                <th className="px-3 py-2 font-medium">Dir</th>
                <th className="px-3 py-2 font-medium">Entry</th>
                <th className="px-3 py-2 font-medium">Exit</th>
                <th className="px-3 py-2 font-medium">Reason</th>
                <th className="px-3 py-2 font-medium">Regime</th>
                <th className="px-3 py-2 text-right font-medium">Bars</th>
                <th className="px-3 py-2 text-right font-medium">PnL</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t, i) => (
                <tr key={i} className="border-b border-[#161820] last:border-0">
                  <td className={cn('px-3 py-2 font-semibold', t.direction === 'LONG' ? 'text-green-400' : 'text-red-400')}>{t.direction}</td>
                  <td className="mono px-3 py-2 text-slate-300">{num(t.entry_price)}<span className="text-slate-600"> · {hhmm(t.entry_ts)}</span></td>
                  <td className="mono px-3 py-2 text-slate-300">{num(t.exit_price)}<span className="text-slate-600"> · {hhmm(t.exit_ts)}</span></td>
                  <td className="px-3 py-2 text-slate-400">{t.exit_reason}</td>
                  <td className="mono px-3 py-2 text-slate-400">{t.regime ?? '—'}</td>
                  <td className="mono px-3 py-2 text-right text-slate-400">{t.hold_bars ?? '—'}</td>
                  <td className={cn('mono px-3 py-2 text-right font-semibold', (t.net_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400')}>{num(t.net_pnl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-4 text-[11px] text-slate-500">No closed trades for this window.</div>
        )}
      </div>
    </Card>
  );
}

function StatsCard({ s }: { s: PaperStructure }) {
  const stats = s.stats ?? {};
  const keys = Object.keys(stats);
  return (
    <Card className="flex flex-col">
      <CardHeader title="Performance" subtitle="Backtest summary" />
      <div className="flex-1 p-4">
        {keys.length ? (
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
            {keys.map((k) => (
              <div key={k} className="flex items-center justify-between">
                <span className="text-slate-500">{k}</span>
                <span className="mono text-slate-200">{String(stats[k])}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-[11px] text-slate-500">No stats.</p>
        )}
      </div>
    </Card>
  );
}

function PortfolioSummary({ data, investment, onInvestment, riskPct, onRiskPct }:
  { data: PaperState; investment: number; onInvestment: (v: number) => void;
    riskPct: number; onRiskPct: (v: number) => void }) {
  const plan = useMemo(() => {
    // gather actioned trades across structures, replay in chronological (exit) order
    const trades: PaperTrade[] = [];
    for (const k of Object.keys(data)) {
      const s = data[k];
      if (!s || s.error || s.watch_only) continue;   // skip errored + watch-only (not actioned)
      for (const t of s.trades ?? []) trades.push(t);
    }
    trades.sort((a, b) => new Date(a.exit_ts).getTime() - new Date(b.exit_ts).getTime());

    const structs = new Set(
      Object.keys(data).filter((k) => data[k] && !data[k].error && !data[k].watch_only),
    ).size;

    let equity = investment;
    let n = 0, wins = 0;
    for (const t of trades) {
      if (equity <= 0) break;                         // ruin — stop trading
      n += 1;
      if (t.win) wins += 1;
      const entry = t.entry_price ?? 0;
      const stop = t.stop;
      // fixed-fractional sizing: risk riskPct of current equity to the planned stop
      const perContractRisk = stop != null ? Math.abs(stop - entry) * CONTRACT_BBL : 0;
      const riskBudget = (riskPct / 100) * equity;
      const contracts = perContractRisk > 0 ? riskBudget / perContractRisk : 0;
      equity += (t.net_pnl ?? 0) * CONTRACT_BBL * contracts;   // compound off equity
    }
    const pnl = equity - investment;
    return { n, structs, winRate: n ? wins / n : null, equity, pnl,
             retPct: investment > 0 ? (pnl / investment) * 100 : null };
  }, [data, investment, riskPct]);

  const netAccent = plan.pnl >= 0 ? 'text-green-400' : 'text-red-400';

  return (
    <Card>
      <CardHeader
        title="Portfolio"
        subtitle={`Aggregate across ${plan.structs} actioned structure${plan.structs === 1 ? '' : 's'} · fixed-% risk, compounding`}
      />
      <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 lg:grid-cols-5">
        <Metric label="Total Trades" value={String(plan.n)} />
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Investment</p>
          <div className="mt-0.5 flex items-center gap-1">
            <span className="mono text-lg font-semibold text-slate-400">$</span>
            <input
              type="number"
              min={0}
              step={1000}
              value={investment}
              onChange={(e) => onInvestment(Math.max(0, Number(e.target.value) || 0))}
              className="mono w-full min-w-0 rounded border border-[#1f2230] bg-[#0e1016] px-1.5 py-0.5 text-lg font-semibold text-slate-100 outline-none focus:border-sky-500/50"
            />
          </div>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-slate-500">Risk / Trade</p>
          <div className="mt-0.5 flex items-center gap-1">
            <input
              type="number"
              min={0}
              step={0.25}
              value={riskPct}
              onChange={(e) => onRiskPct(Math.max(0, Number(e.target.value) || 0))}
              className="mono w-full min-w-0 rounded border border-[#1f2230] bg-[#0e1016] px-1.5 py-0.5 text-lg font-semibold text-slate-100 outline-none focus:border-sky-500/50"
            />
            <span className="mono text-lg font-semibold text-slate-400">%</span>
          </div>
        </div>
        <Metric
          label="Win Rate"
          value={plan.winRate == null ? '—' : `${(plan.winRate * 100).toFixed(1)}%`}
        />
        <Metric
          label="Net PnL"
          value={`${money(plan.pnl)}${plan.retPct != null ? `  (${plan.retPct >= 0 ? '+' : ''}${plan.retPct.toFixed(2)}%)` : ''}`}
          accent={netAccent}
        />
      </div>
    </Card>
  );
}

// ---- Portfolio (all instruments combined) -----------------------------------
const PORTFOLIO_KEY = '__portfolio__';

interface TaggedTrade extends PaperTrade {
  _key: string;
  _label: string;
}

function gatherTrades(data: PaperState): TaggedTrade[] {
  const all: TaggedTrade[] = [];
  for (const k of Object.keys(data)) {
    const s = data[k];
    if (!s || s.error || s.watch_only) continue;   // actioned structures only
    for (const t of s.trades ?? []) all.push({ ...t, _key: k, _label: s.label ?? k });
  }
  all.sort((a, b) => new Date(a.exit_ts).getTime() - new Date(b.exit_ts).getTime());
  return all;
}

function PortfolioEquityCurve({ data, investment, riskPct }:
  { data: PaperState; investment: number; riskPct: number }) {
  const curve = useMemo(() => {
    const trades = gatherTrades(data);
    let equity = investment;
    const pts: { t: string; equity: number }[] = [{ t: 'start', equity }];
    for (const t of trades) {
      if (equity <= 0) break;
      const entry = t.entry_price ?? 0;
      const stop = t.stop;
      const perContractRisk = stop != null ? Math.abs(stop - entry) * CONTRACT_BBL : 0;
      const contracts = perContractRisk > 0 ? ((riskPct / 100) * equity) / perContractRisk : 0;
      equity += (t.net_pnl ?? 0) * CONTRACT_BBL * contracts;
      pts.push({ t: hhmm(t.exit_ts), equity });
    }
    return pts;
  }, [data, investment, riskPct]);

  return (
    <Card className="flex h-[340px] flex-col">
      <CardHeader title="Portfolio Equity Curve" subtitle="All instruments · fixed-% risk, compounding" />
      <div className="flex-1 p-2">
        {curve.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={curve} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
              <defs>
                <linearGradient id="port-eq-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
              <XAxis dataKey="t" {...axisProps} minTickGap={40} />
              <YAxis {...axisProps} domain={['auto', 'auto']} width={64} tickFormatter={(v) => money(Number(v))} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2d3e' }} />
              <ReferenceLine y={investment} stroke="#2a2d3e" strokeDasharray="4 3" />
              <Area type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={1.75} fill="url(#port-eq-grad)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-[11px] text-slate-500">No closed trades yet</div>
        )}
      </div>
    </Card>
  );
}

function AllOpenPositions({ data }: { data: PaperState }) {
  const open = useMemo(() => {
    const rows: { key: string; label: string; p: NonNullable<PaperStructure['open_position']> }[] = [];
    for (const k of Object.keys(data)) {
      const s = data[k];
      if (!s || s.error || s.watch_only || !s.open_position) continue;
      rows.push({ key: k, label: s.label ?? k, p: s.open_position });
    }
    return rows;
  }, [data]);

  return (
    <Card className="flex h-[340px] flex-col">
      <CardHeader title="Open Positions" subtitle={`${open.length} live`} />
      <div className="flex-1 space-y-2 overflow-y-auto p-3">
        {open.length ? (
          open.map(({ key, label, p }) => {
            const pnlAccent = (p.unrealized_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400';
            return (
              <div key={key} className="rounded border border-[#1f2230] bg-[#0e1016] p-2.5 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-200">{label}</span>
                  <span className={cn('rounded px-1.5 py-0.5 text-[10px] font-bold', p.direction === 'LONG' ? 'bg-green-500/15 text-green-400' : 'bg-red-500/15 text-red-400')}>{p.direction}</span>
                </div>
                <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-slate-400">
                  <span>Entry <span className="mono text-slate-300">{num(p.entry_price)}</span></span>
                  <span>Cur <span className="mono text-slate-300">{num(p.current_price)}</span></span>
                  <span>Z <span className="mono text-slate-300">{num(p.current_z, 2)}</span></span>
                  <span>T/S <span className="mono text-slate-300">{num(p.target)}/{num(p.stop)}</span></span>
                  <span className="col-span-2">uPnL <span className={cn('mono', pnlAccent)}>{num(p.unrealized_pnl)}</span></span>
                </div>
              </div>
            );
          })
        ) : (
          <div className="flex h-full items-center justify-center text-[11px] text-slate-500">Flat — no open positions</div>
        )}
      </div>
    </Card>
  );
}

function AllTradesBlotter({ data }: { data: PaperState }) {
  const trades = useMemo(() => gatherTrades(data).slice().reverse(), [data]);  // newest first
  return (
    <Card className="flex flex-col">
      <CardHeader title="Trade Log" subtitle={`${trades.length} closed trade${trades.length === 1 ? '' : 's'} · all instruments`} />
      <div className="overflow-x-auto">
        {trades.length ? (
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-[#1f2230] text-left text-slate-500">
                <th className="px-3 py-2 font-medium">Instrument</th>
                <th className="px-3 py-2 font-medium">Dir</th>
                <th className="px-3 py-2 font-medium">Entry</th>
                <th className="px-3 py-2 font-medium">Exit</th>
                <th className="px-3 py-2 font-medium">Reason</th>
                <th className="px-3 py-2 font-medium">Regime</th>
                <th className="px-3 py-2 text-right font-medium">Bars</th>
                <th className="px-3 py-2 text-right font-medium">PnL</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((t, i) => (
                <tr key={i} className="border-b border-[#161820] last:border-0">
                  <td className="px-3 py-2 font-medium text-slate-300">{t._label}</td>
                  <td className={cn('px-3 py-2 font-semibold', t.direction === 'LONG' ? 'text-green-400' : 'text-red-400')}>{t.direction}</td>
                  <td className="mono px-3 py-2 text-slate-300">{num(t.entry_price)}<span className="text-slate-600"> · {hhmm(t.entry_ts)}</span></td>
                  <td className="mono px-3 py-2 text-slate-300">{num(t.exit_price)}<span className="text-slate-600"> · {hhmm(t.exit_ts)}</span></td>
                  <td className="px-3 py-2 text-slate-400">{t.exit_reason}</td>
                  <td className="mono px-3 py-2 text-slate-400">{t.regime ?? '—'}</td>
                  <td className="mono px-3 py-2 text-right text-slate-400">{t.hold_bars ?? '—'}</td>
                  <td className={cn('mono px-3 py-2 text-right font-semibold', (t.net_pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400')}>{num(t.net_pnl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-4 text-[11px] text-slate-500">No closed trades.</div>
        )}
      </div>
    </Card>
  );
}

function PortfolioView({ data, investment, riskPct }:
  { data: PaperState; investment: number; riskPct: number }) {
  return (
    <>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="lg:col-span-3">
          <PortfolioEquityCurve data={data} investment={investment} riskPct={riskPct} />
        </div>
        <div className="lg:col-span-1">
          <AllOpenPositions data={data} />
        </div>
      </div>
      <AllTradesBlotter data={data} />
    </>
  );
}

// ---- Backtest view (full-history intraday, model engine, flat 1-contract) ----

function ymd(iso: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return '—';
  return `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, '0')}-${String(t.getDate()).padStart(2, '0')}`;
}

function ymdhm(iso: string | null): string {
  if (!iso) return '—';
  const t = new Date(iso);
  if (Number.isNaN(t.getTime())) return '—';
  return `${ymd(iso)} ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`;
}

// fixed-fractional sizing replayed chronologically off realized equity, with a
// per-trade PnL trail (aligned back to newest-first display order).
interface SizedBacktest {
  curve: { t: string; equity: number }[];
  pnlByDisplay: number[];      // sized $ PnL per trade, newest-first (matches bt.trades)
  contractsByDisplay: number[];
  final: number;
  pnl: number;
  maxdd: number;
  maxContracts: number;
  ruined: boolean;
}

function sizeBacktest(trades: BacktestTrade[], investment: number, riskPct: number): SizedBacktest {
  const chrono = [...trades].reverse();         // oldest first for the replay
  let equity = investment;
  let peak = equity, maxdd = 0, maxContracts = 0;
  let ruined = false;
  const curve: { t: string; equity: number }[] = [{ t: 'start', equity }];
  const pnlChrono: number[] = [];
  const contractsChrono: number[] = [];
  for (const t of chrono) {
    if (equity <= 0) { ruined = true; pnlChrono.push(0); contractsChrono.push(0); continue; }
    const entry = t.entry_price ?? 0;
    const stop = t.stop;
    const perContractRisk = stop != null ? Math.abs(stop - entry) * CONTRACT_BBL : 0;
    const contracts = perContractRisk > 0 ? ((riskPct / 100) * equity) / perContractRisk : 0;
    const pnl = (t.net_pnl_pts ?? 0) * CONTRACT_BBL * contracts;
    maxContracts = Math.max(maxContracts, contracts);
    pnlChrono.push(pnl);
    contractsChrono.push(contracts);
    equity += pnl;
    peak = Math.max(peak, equity);
    maxdd = Math.min(maxdd, equity - peak);
    curve.push({ t: ymd(t.exit_ts), equity });
  }
  return {
    curve,
    pnlByDisplay: pnlChrono.reverse(),
    contractsByDisplay: contractsChrono.reverse(),
    final: equity,
    pnl: equity - investment,
    maxdd,
    maxContracts,
    ruined,
  };
}

function BacktestEquityCurve({ curve, start }: { curve: { t: string; equity: number }[]; start: number }) {
  return (
    <Card className="flex h-[360px] flex-col">
      <CardHeader title="Backtest Equity Curve" subtitle="All instruments · fixed-% risk, compounding" />
      <div className="flex-1 p-2">
        {curve.length > 1 ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={curve} margin={{ top: 8, right: 12, bottom: 0, left: 4 }}>
              <defs>
                <linearGradient id="bt-eq-grad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
              <XAxis dataKey="t" {...axisProps} minTickGap={60} />
              <YAxis {...axisProps} domain={['auto', 'auto']} width={64} tickFormatter={(v) => money(Number(v))} />
              <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2d3e' }} />
              <ReferenceLine y={start} stroke="#2a2d3e" strokeDasharray="4 3" />
              <Area type="monotone" dataKey="equity" stroke="#10b981" strokeWidth={1.75} fill="url(#bt-eq-grad)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="flex h-full items-center justify-center text-[11px] text-slate-500">No backtest trades.</div>
        )}
      </div>
    </Card>
  );
}

function BacktestBreakdown({ bt }: { bt: BacktestResult }) {
  return (
    <Card className="flex h-[360px] flex-col">
      <CardHeader title="By Instrument" subtitle="Per-structure · win rate (sizing-independent)" />
      <div className="flex-1 space-y-3 overflow-y-auto p-3">
        {bt.structures.map((s) => (
          <div key={s.key} className="rounded border border-[#1f2230] bg-[#0e1016] p-3 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200">{s.label}</span>
              <span className="mono text-slate-300">{s.win_rate.toFixed(1)}% win</span>
            </div>
            <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-slate-400">
              <span>Trades <span className="mono text-slate-300">{s.n_trades}</span></span>
              <span>1-ctr <span className={cn('mono', s.net_pnl_usd >= 0 ? 'text-green-400' : 'text-red-400')}>{money(s.net_pnl_usd)}</span></span>
              <span className="col-span-2 text-slate-600">{ymd(s.first_trade ?? null)} → {ymd(s.last_trade ?? null)}</span>
            </div>
          </div>
        ))}
        {bt.open_positions.length === 0 ? (
          <div className="rounded border border-[#1f2230] bg-[#0e1016] p-3 text-center text-[11px] text-slate-500">
            Flat at end of history — no open positions
          </div>
        ) : (
          bt.open_positions.map((op) => (
            <div key={op.key} className="rounded border border-amber-500/30 bg-amber-500/5 p-3 text-[11px]">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200">{op.label}</span>
                <span className={cn('mono font-semibold', op.direction === 'LONG' ? 'text-green-400' : 'text-red-400')}>
                  {op.direction} · open
                </span>
              </div>
              <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1 text-slate-400">
                <span>Entry <span className="mono text-slate-300">{op.entry_price?.toFixed(3)}</span></span>
                <span>Target <span className="mono text-slate-300">{op.target?.toFixed(3)}</span></span>
                <span>Stop <span className="mono text-slate-300">{op.stop?.toFixed(3)}</span></span>
                <span className="col-span-2 text-slate-600">since {ymd(op.entry_ts)} · {op.regime ?? '?'}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </Card>
  );
}

function BacktestBlotter({ trades, pnl, contracts, cap }:
  { trades: BacktestTrade[]; pnl: number[]; contracts: number[]; cap: number }) {
  const shown = Math.min(cap, trades.length);
  return (
    <Card className="flex flex-col">
      <CardHeader title="Trade Log" subtitle={`Latest ${shown} of ${trades.length} backtest trades · newest first · sized PnL`} />
      <div className="overflow-x-auto">
        {trades.length ? (
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-[#1f2230] text-left text-slate-500">
                <th className="px-3 py-2 font-medium">Instrument</th>
                <th className="px-3 py-2 font-medium">Dir</th>
                <th className="px-3 py-2 font-medium">Entry</th>
                <th className="px-3 py-2 font-medium">Exit</th>
                <th className="px-3 py-2 font-medium">Reason</th>
                <th className="px-3 py-2 font-medium">Regime</th>
                <th className="px-3 py-2 text-right font-medium">Ctrs</th>
                <th className="px-3 py-2 text-right font-medium">PnL ($)</th>
              </tr>
            </thead>
            <tbody>
              {trades.slice(0, cap).map((t, i) => (
                <tr key={i} className="border-b border-[#161820] last:border-0">
                  <td className="px-3 py-2 font-medium text-slate-300">{t.label}</td>
                  <td className={cn('px-3 py-2 font-semibold', t.direction === 'LONG' ? 'text-green-400' : 'text-red-400')}>{t.direction}</td>
                  <td className="mono px-3 py-2 text-slate-300">{num(t.entry_price)}<span className="text-slate-600"> · {ymdhm(t.entry_ts)}</span></td>
                  <td className="mono px-3 py-2 text-slate-300">{num(t.exit_price)}<span className="text-slate-600"> · {ymdhm(t.exit_ts)}</span></td>
                  <td className="px-3 py-2 text-slate-400">{t.exit_reason}</td>
                  <td className="mono px-3 py-2 text-slate-400">{t.regime ?? '—'}</td>
                  <td className="mono px-3 py-2 text-right text-slate-400">{contracts[i] != null ? contracts[i].toFixed(1) : '—'}</td>
                  <td className={cn('mono px-3 py-2 text-right font-semibold', (pnl[i] ?? 0) >= 0 ? 'text-green-400' : 'text-red-400')}>{money(pnl[i] ?? 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-4 text-[11px] text-slate-500">No backtest trades.</div>
        )}
      </div>
    </Card>
  );
}

function BacktestView({ investment, onInvestment, riskPct, onRiskPct }:
  { investment: number; onInvestment: (v: number) => void; riskPct: number; onRiskPct: (v: number) => void }) {
  const { data: bt, isLoading, error } = usePaperBacktest();

  const sized = useMemo(
    () => (bt?.available ? sizeBacktest(bt.trades, investment, riskPct) : null),
    [bt, investment, riskPct],
  );

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }
  if (error || !bt) {
    return <Card className="p-6 text-center text-[12px] text-slate-500">Failed to load backtest results.</Card>;
  }
  if (!bt.available || !sized) {
    return <Card className="p-6 text-center text-[12px] text-slate-500">No backtest cache found. Run backtest_intraday.py to generate it.</Card>;
  }

  const sm = bt.summary;
  const netAccent = sized.pnl >= 0 ? 'text-green-400' : 'text-red-400';
  const retPct = investment > 0 ? (sized.pnl / investment) * 100 : null;

  return (
    <>
      <Card>
        <CardHeader
          title="Backtest Summary"
          subtitle={`Model engine (regime fair-value z) · entry |z| 1.0–2.0 · fixed-% risk, compounding · ${ymd(sm.first_bar ?? null)} → ${ymd(sm.last_bar ?? null)}`}
        />
        <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-3 lg:grid-cols-6">
          <Metric label="Total Trades" value={String(sm.n_trades)} />
          <Metric label="Win Rate" value={`${sm.win_rate.toFixed(1)}%`} />
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Investment</p>
            <div className="mt-0.5 flex items-center gap-1">
              <span className="mono text-lg font-semibold text-slate-400">$</span>
              <input
                type="number" min={0} step={1000} value={investment}
                onChange={(e) => onInvestment(Math.max(0, Number(e.target.value) || 0))}
                className="mono w-full min-w-0 rounded border border-[#1f2230] bg-[#0e1016] px-1.5 py-0.5 text-lg font-semibold text-slate-100 outline-none focus:border-sky-500/50"
              />
            </div>
          </div>
          <div>
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Risk / Trade</p>
            <div className="mt-0.5 flex items-center gap-1">
              <input
                type="number" min={0} step={0.1} value={riskPct}
                onChange={(e) => onRiskPct(Math.max(0, Number(e.target.value) || 0))}
                className="mono w-full min-w-0 rounded border border-[#1f2230] bg-[#0e1016] px-1.5 py-0.5 text-lg font-semibold text-slate-100 outline-none focus:border-sky-500/50"
              />
              <span className="mono text-lg font-semibold text-slate-400">%</span>
            </div>
          </div>
          <Metric
            label="Net PnL"
            value={`${money(sized.pnl)}${retPct != null ? `  (${retPct >= 0 ? '+' : ''}${retPct.toFixed(0)}%)` : ''}`}
            accent={netAccent}
          />
          <Metric label="Max Drawdown" value={money(sized.maxdd)} accent="text-red-400" />
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-1 border-t border-[#1f2230] px-4 py-2 text-[11px] text-slate-400">
          <span>Final equity <span className="mono text-slate-200">{money(sized.final)}</span></span>
          <span>Peak position <span className="mono text-slate-200">{sized.maxContracts.toFixed(0)} contracts</span></span>
          {sized.ruined && <span className="font-semibold text-red-400">RUIN — equity hit 0; lower risk %</span>}
          <span className="ml-auto text-slate-600">sizing risks {riskPct}% of equity to the stop per trade</span>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="lg:col-span-3">
          <BacktestEquityCurve curve={sized.curve} start={investment} />
        </div>
        <div className="lg:col-span-1">
          <BacktestBreakdown bt={bt} />
        </div>
      </div>

      <BacktestBlotter
        trades={bt.trades}
        pnl={sized.pnlByDisplay}
        contracts={sized.contractsByDisplay}
        cap={bt.display_cap ?? 80}
      />
    </>
  );
}

type Mode = 'live' | 'backtest';

function ModeToggle({ mode, onMode }: { mode: Mode; onMode: (m: Mode) => void }) {
  const opts: { id: Mode; label: string }[] = [
    { id: 'live', label: 'Live' },
    { id: 'backtest', label: 'Backtest' },
  ];
  return (
    <div className="inline-flex rounded-md border border-[#1f2230] bg-[#0e1016] p-0.5">
      {opts.map((o) => (
        <button
          key={o.id}
          onClick={() => onMode(o.id)}
          className={cn(
            'rounded px-3 py-1 text-[12px] font-medium transition-colors',
            mode === o.id ? 'bg-sky-500/15 text-sky-300' : 'text-slate-400 hover:text-slate-200',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// live data-age chip: how old is the freshest closed bar across all structures.
// as_of is a tz-naive UTC ISO string (e.g. "2026-06-18T05:30:00"); parse as UTC.
function parseUtc(iso: string): number {
  const hasTz = iso.endsWith('Z') || /[+-]\d\d:?\d\d$/.test(iso);
  return Date.parse(hasTz ? iso : iso + 'Z');
}

function DataFreshness({ data }: { data: PaperState | undefined }) {
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((n) => n + 1), 30_000);  // refresh the age text
    return () => clearInterval(id);
  }, []);

  const latest = useMemo(() => {
    if (!data) return null;
    let ms: number | null = null;
    for (const k of Object.keys(data)) {
      const s = data[k];
      if (!s || s.error || !s.as_of) continue;
      const t = parseUtc(s.as_of);
      if (!Number.isNaN(t) && (ms == null || t > ms)) ms = t;
    }
    return ms;
  }, [data]);

  if (latest == null) return null;
  const ageMin = Math.max(0, Math.round((Date.now() - latest) / 60_000));
  const status = ageMin <= 35 ? 'live' : ageMin <= 90 ? 'pre' : 'warning';
  const age =
    ageMin < 1 ? 'just now'
    : ageMin < 60 ? `${ageMin}m ago`
    : `${Math.floor(ageMin / 60)}h ${ageMin % 60}m ago`;
  const d = new Date(latest);
  const barUtc = `${String(d.getUTCHours()).padStart(2, '0')}:${String(d.getUTCMinutes()).padStart(2, '0')}`;
  return (
    <span className="inline-flex items-center gap-2 rounded-md border border-[#1f2230] bg-[#0e1016] px-2.5 py-1 text-[11px]">
      <StatusDot status={status} />
      <span className="text-slate-400">Last bar <span className="mono text-slate-200">{barUtc} UTC</span></span>
      <span className="text-slate-600">· {age}</span>
    </span>
  );
}

export function PaperTrading() {
  const { data, isLoading, isFetching, refetch } = usePaperState();
  const [mode, setMode] = useState<Mode>('live');
  const [active, setActive] = useState<string>(PORTFOLIO_KEY);
  const [investment, setInvestment] = useState<number>(100000);
  const [riskPct, setRiskPct] = useState<number>(1);
  // backtest sizing is independent of the live portfolio inputs
  const [btInvestment, setBtInvestment] = useState<number>(100000);
  const [btRiskPct, setBtRiskPct] = useState<number>(1);

  const keys = useMemo(() => {
    if (!data) return ORDER;
    return ORDER.filter((k) => k in data).concat(Object.keys(data).filter((k) => !ORDER.includes(k)));
  }, [data]);

  const current = data?.[active];

  return (
    <div className="space-y-4">
      <PageHeader
        title="Paper Trading"
        description="Daily fair value · intraday z-score mean reversion"
        actions={
          <div className="flex items-center gap-3">
            {mode === 'live' && <DataFreshness data={data} />}
            <ModeToggle mode={mode} onMode={setMode} />
            {mode === 'live' && (
              <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
                <RefreshCw className={cn('h-3.5 w-3.5', isFetching && 'animate-spin')} />
                Refresh
              </Button>
            )}
          </div>
        }
      />

      {mode === 'backtest' ? (
        <BacktestView investment={btInvestment} onInvestment={setBtInvestment} riskPct={btRiskPct} onRiskPct={setBtRiskPct} />
      ) : isLoading ? (
        <div className="space-y-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      ) : !data ? (
        <Card className="p-6 text-center text-[12px] text-slate-500">Failed to load paper-trading state.</Card>
      ) : (
        <>
          <PortfolioSummary data={data} investment={investment} onInvestment={setInvestment} riskPct={riskPct} onRiskPct={setRiskPct} />

          <Tabs
            tabs={[{ id: PORTFOLIO_KEY, label: 'Portfolio' }, ...keys.map((k) => ({ id: k, label: data[k]?.label ?? k }))]}
            value={active}
            onChange={setActive}
          />

          {active === PORTFOLIO_KEY ? (
            <PortfolioView data={data} investment={investment} riskPct={riskPct} />
          ) : !current ? (
            <Card className="p-6 text-center text-[12px] text-slate-500">Select a structure.</Card>
          ) : current.error ? (
            <Card className="p-4">
              <div className="flex items-center gap-2">
                <StatusDot status="warning" />
                <span className="text-[12px] text-amber-400">{current.error}</span>
              </div>
            </Card>
          ) : (
            <>
              <FairPriceBlock s={current} />

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <SignalPanel s={current} />
                <OpenPositionCard s={current} />
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ZScoreChart s={current} />
                <EquityCurve s={current} />
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <TradeBlotter s={current} />
                </div>
                <StatsCard s={current} />
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
