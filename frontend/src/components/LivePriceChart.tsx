import { useMemo, useState, useRef, useEffect } from 'react';
import { ChevronDown, Wifi, WifiOff } from 'lucide-react';
import { ChartCard } from '@/components/ChartCard';
import { AreaChartPro } from '@/components/charts';
import { Skeleton } from '@/components/ui';
import { useQuote, useHistory } from '@/hooks/useQuotes';
import { YAHOO_SYMBOLS, YAHOO_MACRO, YAHOO_PRODUCTS, type SymbolDef } from '@/lib/symbols';
import { formatPrice, formatPercent, cn } from '@/lib/utils';

// Dubai crude has no free daily feed (not on Yahoo). We show it as an indicative
// series derived from live Brent minus a fixed Brent–Dubai EFS spread.
const DUBAI_EFS = 2.0; // USD/bbl; Dubai typically trades ~$2 below Brent
const DUBAI: SymbolDef = {
  id: 'dubai', yahoo: 'BZ=F', name: 'Dubai Crude', unit: 'bbl', currency: 'USD', category: 'crude',
};

// Commodities available for the live chart (Yahoo-served + the Dubai proxy).
const SELECTABLE: SymbolDef[] = [...YAHOO_SYMBOLS, DUBAI, ...YAHOO_PRODUCTS, ...YAHOO_MACRO];

// Range tabs mirror Yahoo Finance's own chart selector. Label -> Yahoo range param.
const RANGE_MAP: Record<string, string> = {
  '1D': '1d',
  '5D': '5d',
  '1M': '1mo',
  '6M': '6mo',
  '1Y': '1y',
  '5Y': '5y',
};
const RANGES = Object.keys(RANGE_MAP);

const INTRADAY = new Set(['1D', '5D']);

function formatPoint(epochSec: number, range: string): string {
  const d = new Date(epochSec * 1000);
  if (INTRADAY.has(range)) {
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  }
  if (range === '5Y') {
    return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
  }
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export function LivePriceChart({ defaultId = 'brent' }: { defaultId?: string }) {
  const [id, setId] = useState(defaultId);
  const [range, setRange] = useState('1M');
  const [open, setOpen] = useState(false);
  const selectorRef = useRef<HTMLDivElement>(null);

  // Close the dropdown when clicking anywhere outside it.
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: MouseEvent) => {
      if (selectorRef.current && !selectorRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [open]);

  const sym = SELECTABLE.find((s) => s.id === id) ?? SELECTABLE[0];
  // Dubai is synthetic: fetch Brent, then shift by the EFS spread.
  const isDubai = id === 'dubai';
  const fetchId = isDubai ? 'brent' : id;
  const offset = isDubai ? -DUBAI_EFS : 0;
  const { quote, isError: quoteError } = useQuote(fetchId, 'all');
  const { data: history, isLoading, isError: histError } = useHistory(fetchId, RANGE_MAP[range]);

  const chartData = useMemo(
    () => (history?.points ?? []).map((p) => ({ time: formatPoint(p.time, range), value: p.value + offset })),
    [history, range, offset]
  );

  const up = (quote?.changePct ?? 0) >= 0;
  const color = up ? '#10b981' : '#ef4444';
  const live = !quoteError && !!quote && !quote.stale;
  const ccy = quote?.currency === 'USD' ? '$' : quote?.currency === 'EUR' ? '€' : '';

  const selector = (
    <div className="relative" ref={selectorRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 rounded-md border border-[#2a2d3e] bg-[#0a0b0d] px-2 py-1 text-[12px] font-semibold text-slate-100 transition-colors hover:border-blue-500/40"
      >
        {sym.name}
        <ChevronDown className={cn('h-3.5 w-3.5 text-slate-500 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 max-h-64 w-48 overflow-y-auto rounded-md border border-[#2a2d3e] bg-[#0f1117] py-1 shadow-2xl">
          {SELECTABLE.map((s) => (
            <button
              key={s.id}
              type="button"
              // onMouseDown fires before the trigger's blur, so selection always registers.
              onMouseDown={(e) => { e.preventDefault(); setId(s.id); setOpen(false); }}
              className={cn(
                'flex w-full items-center justify-between px-3 py-1.5 text-left text-[11px] transition-colors hover:bg-[#1c1e27]',
                s.id === id ? 'text-blue-400' : 'text-slate-300'
              )}
            >
              <span>{s.name}</span>
              <span className="text-[9px] uppercase text-slate-600">{s.category}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );

  const priceMeta = quote ? (
    <span className="mono mr-2 flex items-center gap-1.5 text-sm font-semibold text-slate-100">
      {live ? <Wifi className="h-3 w-3 text-green-400" /> : <WifiOff className="h-3 w-3 text-amber-400" />}
      {ccy}{formatPrice(quote.price + offset)}
      <span className={cn('text-[11px]', up ? 'text-green-400' : 'text-red-400')}>{formatPercent(quote.changePct)}</span>
    </span>
  ) : null;

  return (
    <ChartCard
      leftControl={selector}
      subtitle={isDubai
        ? `Indicative · Brent − $${DUBAI_EFS.toFixed(2)} EFS · ${sym.unit} · ${sym.currency}`
        : `${sym.yahoo} · ${sym.unit}${sym.currency ? ` · ${sym.currency}` : ''}`}
      ranges={RANGES}
      range={range}
      onRangeChange={setRange}
      rightMeta={priceMeta}
    >
      {isLoading ? (
        <Skeleton className="h-[210px] w-full" />
      ) : histError || chartData.length === 0 ? (
        <div className="flex h-[210px] items-center justify-center text-[11px] text-slate-600">
          No data available for {sym.name} ({range})
        </div>
      ) : (
        <AreaChartPro data={chartData} color={color} height={210} />
      )}
    </ChartCard>
  );
}
