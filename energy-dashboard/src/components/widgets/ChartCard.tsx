import { useState, type ReactNode } from 'react';
import { Maximize2, MoreHorizontal, Download } from 'lucide-react';
import { Card, CardHeader } from '@/components/ui/Card';
import { Tabs } from '@/components/ui';

export function ChartCard({
  title,
  subtitle,
  children,
  ranges = ['1D', '1W', '1M', '3M', '1Y'],
  defaultRange = '1M',
  rightMeta,
  leftControl,
  range: controlledRange,
  onRangeChange,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  ranges?: string[];
  defaultRange?: string;
  rightMeta?: ReactNode;
  leftControl?: ReactNode;
  range?: string;
  onRangeChange?: (range: string) => void;
}) {
  const [internalRange, setInternalRange] = useState(defaultRange);
  const range = controlledRange ?? internalRange;
  const setRange = (r: string) => {
    setInternalRange(r);
    onRangeChange?.(r);
  };
  return (
    <Card className="flex h-full flex-col">
      <CardHeader
        title={title}
        subtitle={subtitle}
        icon={leftControl}
        action={
          <>
            {rightMeta}
            <Tabs
              tabs={ranges.map((r) => ({ id: r, label: r }))}
              value={range}
              onChange={setRange}
            />
            <button className="flex h-6 w-6 items-center justify-center rounded text-slate-600 hover:bg-[#1c1e27] hover:text-slate-300">
              <Download className="h-3.5 w-3.5" />
            </button>
            <button className="flex h-6 w-6 items-center justify-center rounded text-slate-600 hover:bg-[#1c1e27] hover:text-slate-300">
              <Maximize2 className="h-3.5 w-3.5" />
            </button>
            <button className="flex h-6 w-6 items-center justify-center rounded text-slate-600 hover:bg-[#1c1e27] hover:text-slate-300">
              <MoreHorizontal className="h-3.5 w-3.5" />
            </button>
          </>
        }
      />
      <div className="flex-1 p-3">{children}</div>
    </Card>
  );
}
