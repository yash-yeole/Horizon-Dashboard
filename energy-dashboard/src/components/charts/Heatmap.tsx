import { cn } from '@/lib/utils';
import type { CorrelationEntry } from '@/types';

function corrColor(v: number): string {
  // -1 red, 0 neutral, +1 green
  if (v === 1) return 'rgba(37, 99, 235, 0.45)';
  if (v >= 0) {
    const a = 0.12 + v * 0.45;
    return `rgba(16, 185, 129, ${a})`;
  }
  const a = 0.12 + Math.abs(v) * 0.45;
  return `rgba(239, 68, 68, ${a})`;
}

export function CorrelationHeatmap({
  matrix,
  assets,
}: {
  matrix: CorrelationEntry[];
  assets: string[];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th className="p-1 text-left" />
            {assets.map((a) => (
              <th key={a} className="p-1 text-center text-[9px] font-medium uppercase text-slate-500">
                {a}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row) => (
            <tr key={row.asset}>
              <td className="py-1 pr-2 text-right text-[9px] font-medium uppercase text-slate-500 whitespace-nowrap">
                {row.asset}
              </td>
              {assets.map((a) => {
                const v = row.values[a];
                return (
                  <td key={a} className="p-0.5">
                    <div
                      className={cn(
                        'flex h-9 items-center justify-center rounded text-[10px] font-medium transition-transform hover:scale-105 cursor-default',
                        Math.abs(v) > 0.5 ? 'text-slate-100' : 'text-slate-400'
                      )}
                      style={{ background: corrColor(v) }}
                      title={`${row.asset} / ${a}: ${v.toFixed(2)}`}
                    >
                      {v.toFixed(2)}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
