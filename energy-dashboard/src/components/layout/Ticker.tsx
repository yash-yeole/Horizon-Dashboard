import { HERO_METRICS, CRUDE_GRADES, PRODUCTS } from '@/data/market';
import { formatPercent } from '@/lib/utils';
import { cn } from '@/lib/utils';
import { useQuotes, mergeQuotes } from '@/hooks/useQuotes';

const TAPE = [...HERO_METRICS, ...CRUDE_GRADES, ...PRODUCTS];

export function Ticker() {
  const { data } = useQuotes('all');
  const tape = mergeQuotes(TAPE, data?.quotes);

  return (
    <div className="flex h-7 shrink-0 items-center overflow-hidden border-b border-[#1f2230] bg-[#0f1117]">
      <div className="flex shrink-0 items-center gap-1.5 border-r border-[#1f2230] px-3 h-full">
        <span className="h-1.5 w-1.5 rounded-full bg-green-400 pulse-dot" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Live Tape</span>
      </div>
      <div className="relative flex-1 overflow-hidden">
        <div className="ticker-track flex items-center gap-6 whitespace-nowrap px-4">
          {[...tape, ...tape].map((m, i) => (
            <span key={i} className="flex items-center gap-2 text-[11px]">
              <span className="font-semibold text-slate-300">{m.symbol}</span>
              <span className="mono text-slate-400">{m.price.toLocaleString()}</span>
              <span className={cn('mono text-[10px]', m.changePct >= 0 ? 'text-green-400' : 'text-red-400')}>
                {formatPercent(m.changePct)}
              </span>
            </span>
          ))}
        </div>
      </div>
      <style>{`
        @keyframes ticker { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }
        .ticker-track { animation: ticker 60s linear infinite; }
        .ticker-track:hover { animation-play-state: paused; }
      `}</style>
    </div>
  );
}
