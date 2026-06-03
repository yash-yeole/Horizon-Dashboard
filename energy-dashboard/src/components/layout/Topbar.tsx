import { Search, Bell, ChevronDown, Settings2, Sun, Globe } from 'lucide-react';
import { useClock } from '@/hooks/useClock';
import { useUIStore } from '@/store/useUIStore';
import { StatusDot } from '@/components/ui';

const WATCHLISTS = ['Energy Core', 'Crude Complex', 'Refined Products', 'Macro Hedge', 'Freight'];

export function Topbar() {
  const clock = useClock();
  const watchlist = useUIStore((s) => s.watchlist);
  const setWatchlist = useUIStore((s) => s.setWatchlist);

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-[#1f2230] bg-[#0a0b0d] px-4">
      {/* Search */}
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
        <input
          placeholder="Search markets, instruments, news…"
          className="h-8 w-full rounded-md border border-[#1f2230] bg-[#0f1117] pl-8 pr-12 text-xs text-slate-200 placeholder:text-slate-600 focus:border-blue-500/40 focus:outline-none focus:ring-1 focus:ring-blue-500/20"
        />
        <kbd className="absolute right-2 top-1/2 -translate-y-1/2 rounded border border-[#2a2d3e] bg-[#161820] px-1.5 py-0.5 text-[9px] text-slate-500">
          ⌘K
        </kbd>
      </div>

      {/* Market status */}
      <div className="hidden items-center gap-3 rounded-md border border-[#1f2230] bg-[#0f1117] px-3 py-1.5 lg:flex">
        <StatusDot status="live" label="ICE" />
        <span className="h-3 w-px bg-[#1f2230]" />
        <StatusDot status="live" label="NYMEX" />
        <span className="h-3 w-px bg-[#1f2230]" />
        <StatusDot status="pre" label="CME" />
      </div>

      {/* Watchlist selector */}
      <div className="relative hidden md:block">
        <select
          value={watchlist}
          onChange={(e) => setWatchlist(e.target.value)}
          className="h-8 cursor-pointer appearance-none rounded-md border border-[#1f2230] bg-[#0f1117] pl-3 pr-8 text-xs text-slate-300 focus:border-blue-500/40 focus:outline-none"
        >
          {WATCHLISTS.map((w) => (
            <option key={w} value={w}>{w}</option>
          ))}
        </select>
        <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
      </div>

      {/* UTC clock */}
      <div className="hidden items-center gap-1.5 rounded-md border border-[#1f2230] bg-[#0f1117] px-2.5 py-1.5 sm:flex">
        <Globe className="h-3.5 w-3.5 text-slate-600" />
        <span className="mono text-xs font-medium text-slate-300">{clock}</span>
        <span className="text-[9px] uppercase text-slate-600">UTC</span>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-1">
        <button className="flex h-8 w-8 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-[#161820] hover:text-slate-300">
          <Sun className="h-4 w-4" strokeWidth={1.75} />
        </button>
        <button className="relative flex h-8 w-8 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-[#161820] hover:text-slate-300">
          <Bell className="h-4 w-4" strokeWidth={1.75} />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-red-500 ring-2 ring-[#0a0b0d]" />
        </button>
        <button className="flex h-8 w-8 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-[#161820] hover:text-slate-300">
          <Settings2 className="h-4 w-4" strokeWidth={1.75} />
        </button>

        {/* Profile */}
        <button className="ml-1 flex items-center gap-2 rounded-md border border-[#1f2230] bg-[#0f1117] py-1 pl-1 pr-2 transition-colors hover:border-[#2a2d3e]">
          <div className="flex h-6 w-6 items-center justify-center rounded bg-gradient-to-br from-blue-500 to-purple-500 text-[10px] font-bold text-white">
            YY
          </div>
          <div className="hidden text-left lg:block">
            <p className="text-[11px] font-medium leading-none text-slate-200">Yash. Y</p>
            <p className="text-[9px] text-slate-500">Quant Desk</p>
          </div>
          <ChevronDown className="h-3 w-3 text-slate-600" />
        </button>
      </div>
    </header>
  );
}
