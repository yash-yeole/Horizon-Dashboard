import { Bell, ChevronDown, Settings2, Sun, Globe } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useClock } from '@/hooks/useClock';
import { useAlerts } from '@/components/AlertsProvider';

export function Topbar() {
  const clock = useClock();
  const { unread } = useAlerts();

  return (
    <header className="flex h-12 shrink-0 items-center gap-3 border-b border-[#1f2230] bg-[#0a0b0d] px-4">
      {/* Page title (portaled in by the active page's PageHeader) */}
      <div id="page-chrome-title" className="flex min-w-0 flex-1 items-center" />

      {/* Page actions (portaled in by the active page's PageHeader) */}
      <div id="page-chrome-actions" className="flex items-center gap-2" />

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
        <Link to="/alerts" title="Alerts" className="relative flex h-8 w-8 items-center justify-center rounded-md text-slate-500 transition-colors hover:bg-[#161820] hover:text-slate-300">
          <Bell className="h-4 w-4" strokeWidth={1.75} />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-red-500 px-1 text-[8px] font-bold text-white ring-2 ring-[#0a0b0d]">
              {unread > 9 ? '9+' : unread}
            </span>
          )}
        </Link>
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
