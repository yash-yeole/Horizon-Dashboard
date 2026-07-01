import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, TrendingUp, TrendingDown, Minus, ChevronDown, AlertTriangle } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { SectionTitle } from '@/components/ui';
import { cn } from '@/lib/utils';
import { useReleaseImpact } from '@/hooks/useReleaseImpact';

const BIAS = {
  bullish: { label: 'BULLISH', cls: 'text-green-400', Icon: TrendingUp },
  bearish: { label: 'BEARISH', cls: 'text-red-400', Icon: TrendingDown },
  neutral: { label: 'NEUTRAL', cls: 'text-amber-400', Icon: Minus },
} as const;

const fmtM = (n: number | null | undefined) =>
  n == null ? '—' : `${n > 0 ? '+' : ''}${n.toFixed(1)}M`;
const fmtSigned = (n: number) => `${n > 0 ? '+' : ''}${n.toFixed(1)}`;
const leanCls = (l: string) =>
  l === 'bullish' ? 'text-green-400' : l === 'bearish' ? 'text-red-400' : 'text-slate-400';
const chip = 'rounded bg-slate-800/60 px-1.5 py-0.5 text-[10px] text-slate-300';

/** Compact Dashboard card — our forecast + headline call, links to the full section. */
export function ReleaseImpactCard() {
  const { data, isLoading } = useReleaseImpact();
  if (isLoading || !data) {
    return <Card className="p-3"><div className="text-[11px] text-slate-500">Loading release impact…</div></Card>;
  }
  const b = BIAS[data.bias];
  const countdown = data.daysUntil <= 0 ? 'Today' : `in ${data.daysUntil}d`;
  const surp = data.ourSurpriseVsConsensus;
  const surpLean = surp == null ? 'neutral' : surp <= -1 ? 'bullish' : surp >= 1 ? 'bearish' : 'neutral';
  return (
    <Card hover className="flex flex-col p-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">EIA Release Impact · {data.instrument}</span>
        <span className={chip}>{countdown} · {data.timeEt} ET</span>
      </div>
      <div className={cn('mt-2 flex items-center gap-1.5 text-lg font-bold', b.cls)}>
        <b.Icon className="h-4 w-4" />{b.label}
        <span className="text-[10px] font-normal text-slate-500">({data.confidence} conf.)</span>
      </div>
      {data.ourForecast && (
        <div className="mt-2 rounded bg-slate-800/40 p-2">
          <div className="text-[9px] uppercase tracking-wide text-slate-500">Our forecast</div>
          <div className="text-lg font-bold text-slate-100">{fmtM(data.ourForecast.predictedChange)}</div>
          <div className="text-[10px] text-slate-500">vs consensus {fmtM(data.consensus)} ·{' '}
            <span className={leanCls(surpLean)}>surprise {surp == null ? '—' : `${fmtSigned(surp)}M ${surpLean}`}</span>
          </div>
        </div>
      )}
      <div className="mt-2 truncate text-[10px] text-slate-500">Watch: {data.spreadFocus}</div>
      <Link to="/inventories#release-impact"
            className="mt-2 inline-flex items-center gap-1 text-[11px] font-medium text-sky-400 hover:text-sky-300">
        Full analysis <ArrowRight className="h-3 w-3" />
      </Link>
    </Card>
  );
}

/** Full Inventories section — our forecast + reaction call + expandable model detail. */
export function ReleaseImpactSection() {
  const { data, isLoading, isError } = useReleaseImpact();
  const [expanded, setExpanded] = useState(false);
  if (isLoading) return <Card className="p-4"><div className="text-[12px] text-slate-500">Loading release impact…</div></Card>;
  if (isError || !data) return null;
  const b = BIAS[data.bias];
  const fc = data.ourForecast;
  const surp = data.ourSurpriseVsConsensus;
  const surpLean = surp == null ? 'neutral' : surp <= -1 ? 'bullish' : surp >= 1 ? 'bearish' : 'neutral';
  return (
    <Card id="release-impact" className="flex scroll-mt-20 flex-col p-4">
      <CardHeader
        title={`Inventory Release Impact · ${data.instrument}`}
        subtitle={`Next EIA crude print · ${data.nextReleaseDate} ${data.timeEt} ET${data.isDelayed ? ' (delayed)' : ''} · ${data.daysUntil <= 0 ? 'today' : `in ${data.daysUntil}d`}`}
      />
      <div className="mt-2 flex items-center gap-2">
        <span className={cn('flex items-center gap-1.5 text-xl font-bold', b.cls)}><b.Icon className="h-5 w-5" />{b.label}</span>
        <span className={chip}>{data.confidence} confidence</span>
      </div>
      <p className="mt-1 text-[12px] text-slate-300">{data.headline}</p>

      {/* OUR forecast */}
      {fc && (
        <div className="mt-3 rounded border border-slate-800 bg-slate-800/30 p-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div>
              <div className="text-[9px] uppercase tracking-wide text-slate-500">Our predicted change · wk-ending {fc.targetWeekEnding}</div>
              <div className="text-2xl font-bold text-slate-100">{fmtM(fc.predictedChange)}
                <span className="ml-1 text-[11px] font-normal text-slate-500">± {fc.sd.toFixed(1)}</span>
              </div>
            </div>
            <div className="text-right text-[11px] text-slate-400">
              <div>vs consensus <b className="text-slate-200">{fmtM(data.consensus)}</b></div>
              <div>surprise <b className={leanCls(surpLean)}>{surp == null ? '—' : `${fmtSigned(surp)}M ${surpLean}`}</b></div>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {fc.drivers.map((d) => (
              <span key={d.label} className={chip}>{d.label}: {fmtSigned(d.value)}{d.unit === 'M bbl' ? 'M' : ''}</span>
            ))}
          </div>
          <div className="mt-1.5 text-[10px] text-slate-500">
            Model fit R² {fc.r2.toFixed(2)} · out-of-sample R² {fc.oosR2.toFixed(2)}. {fc.note}
          </div>
        </div>
      )}

      <div className="mt-3"><SectionTitle>If EIA prints…</SectionTitle></div>
      <div className="overflow-hidden rounded border border-slate-800">
        <table className="w-full text-[11px]">
          <thead className="bg-slate-800/40 text-slate-400">
            <tr>
              <th className="p-1.5 text-left font-medium">Print</th>
              <th className="p-1.5 text-right font-medium">vs Consensus</th>
              <th className="p-1.5 text-right font-medium">vs Our fc</th>
              <th className="p-1.5 text-right font-medium">Surprise lean</th>
            </tr>
          </thead>
          <tbody>
            {data.scenarios.map((s) => (
              <tr key={s.actual} className="border-t border-slate-800/60">
                <td className="p-1.5 text-slate-300">{fmtM(s.actual)} <span className="text-slate-500">{s.label}</span></td>
                <td className="p-1.5 text-right text-slate-400">{fmtSigned(s.surpriseVsConsensus)}</td>
                <td className="p-1.5 text-right text-slate-400">{fmtSigned(s.surpriseVsOurs)}</td>
                <td className={cn('p-1.5 text-right font-medium capitalize', leanCls(s.lean))}>{s.lean}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div>
          <SectionTitle>Top-3 factors (war regime)</SectionTitle>
          <ul className="space-y-1">
            {data.topFactors.map((f, i) => (
              <li key={f.name} className="flex items-center justify-between text-[11px]">
                <span className="text-slate-300">{i + 1}. {f.name}</span>
                <span className="text-slate-500">β {f.stdBeta.toFixed(2)}{f.significant ? ' ✓' : ''}</span>
              </li>
            ))}
            <li className="text-[10px] text-slate-600">Inventory surprise ranks below all — event-level, insignificant.</li>
          </ul>
        </div>
        <div>
          <SectionTitle>Products / spreads to watch</SectionTitle>
          <p className="text-[12px] text-slate-300">{data.spreadFocus}</p>
          <ul className="mt-1 space-y-1">
            {data.productEffects.map((p) => (
              <li key={p.product} className="text-[11px]">
                <span className="text-slate-300">{p.spread}</span>
                <span className="text-slate-500"> · β {p.beta.toFixed(2)}{p.significant ? ' ✓' : ''} on {p.channel}</span>
              </li>
            ))}
          </ul>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {data.newsThemes.filter((t) => t.count > 0).map((t) => (
              <span key={t.theme} className={chip}>{t.theme} · {t.count}</span>
            ))}
          </div>
        </div>
      </div>

      <p className="mt-3 text-[12px] leading-relaxed text-slate-400">{data.reasoning}</p>

      <button onClick={() => setExpanded((e) => !e)}
              className="mt-3 inline-flex items-center gap-1 self-start text-[11px] font-medium text-sky-400 hover:text-sky-300">
        {expanded ? 'Hide' : 'Show'} model detail <ChevronDown className={cn('h-3 w-3 transition-transform', expanded && 'rotate-180')} />
      </button>
      {expanded && (
        <div className="mt-2 space-y-2 border-t border-slate-800 pt-2 text-[11px] text-slate-400">
          <div className="flex items-start gap-1.5 text-amber-400/80">
            <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
            <span>WTI inventory beta ≈ {data.inventoryBeta.toFixed(2)} %/Mbbl — small, sub-significant and sign-unstable since 2019. The crude print is a secondary WTI driver; net impact is NEUTRAL. Product cracks (RBOB–WTI, HO–WTI) are the more inventory-sensitive vehicles.</span>
          </div>
          {data.productEffects.map((p) => (
            <div key={p.product}><span className="text-slate-500">{p.product}: </span>{p.note}</div>
          ))}
          <div><span className="text-slate-500">Framework: </span>{data.framework}</div>
          {data.headlines.length > 0 && (
            <div>
              <div className="text-slate-500">Recent headlines driving the tape:</div>
              <ul className="mt-0.5 space-y-0.5">
                {data.headlines.map((h, i) => <li key={i} className="truncate">· {h}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
      {data.stale && <div className="mt-2 text-[10px] text-amber-500/70">Serving cached data (upstream unavailable).</div>}
    </Card>
  );
}
