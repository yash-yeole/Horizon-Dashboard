import { motion } from 'framer-motion';
import { ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { Sparkline } from '@/components/charts';
import { formatPrice, formatChange, formatPercent, cn } from '@/lib/utils';
import type { Commodity } from '@/types';

export function MetricCard({ data, delay = 0 }: { data: Commodity; delay?: number }) {
  const up = data.changePct >= 0;
  const color = up ? '#10b981' : '#ef4444';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay }}
      whileHover={{ y: -2 }}
      className="group relative overflow-hidden rounded-lg border border-[#1f2230] bg-[#0f1117] p-3 transition-colors hover:border-[#2a2d3e]"
    >
      <div className="flex items-start justify-between">
        <div className="min-w-0">
          <p className="truncate text-[11px] font-semibold uppercase tracking-wide text-slate-400">{data.name}</p>
          <p className="text-[9px] text-slate-600">{data.symbol}</p>
        </div>
        <span
          className={cn(
            'flex items-center gap-0.5 rounded px-1 py-0.5 text-[10px] font-medium',
            up ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
          )}
        >
          {up ? <ArrowUpRight className="h-3 w-3" /> : <ArrowDownRight className="h-3 w-3" />}
          {formatPercent(data.changePct)}
        </span>
      </div>

      <div className="mt-2 flex items-end justify-between gap-2">
        <div>
          <p className="mono text-lg font-semibold leading-none text-slate-100">
            {data.currency === 'USD' && '$'}
            {formatPrice(data.price, data.price < 10 ? 2 : 2)}
          </p>
          <p className={cn('mono mt-1 text-[10px]', up ? 'text-green-400' : 'text-red-400')}>
            {formatChange(data.change)} <span className="text-slate-600">{data.unit}</span>
          </p>
        </div>
        <div className="h-8 w-20 shrink-0">
          <Sparkline data={data.sparkline} color={color} height={32} />
        </div>
      </div>
    </motion.div>
  );
}
