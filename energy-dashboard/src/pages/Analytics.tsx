import { useState } from 'react';
import { motion, Reorder } from 'framer-motion';
import { GripVertical, Plus, Save, LayoutGrid } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui';
import { MultiLineChart, AreaChartPro, SpreadBars } from '@/components/charts';
import { CorrelationHeatmap } from '@/components/charts/Heatmap';
import { SpreadMonitor, MarketMovers } from '@/components/widgets/Panels';
import { LeadLagAnalysis } from '@/components/widgets/LeadLagAnalysis';
import { comparisonSeries, brentSeries, correlationMatrix, CORRELATION_ASSETS } from '@/data/series';
import { useQuotes } from '@/hooks/useQuotes';
import { useCorrelation, useComparison, useSeries, ENERGY_ASSETS } from '@/hooks/useHistory';
import { computeSpreads } from '@/lib/spreads';
import { realizedVol } from '@/lib/analytics';

interface Panel { id: string; title: string; type: string; }

const INITIAL: Panel[] = [
  { id: 'p1', title: 'Multi-Asset Comparison', type: 'multiline' },
  { id: 'p2', title: 'Volatility Surface', type: 'area' },
  { id: 'p3', title: 'Correlation Explorer', type: 'corr' },
  { id: 'p4', title: 'Spread Monitor', type: 'spreads' },
];

const VOL_COLORS: Record<string, string> = {
  Brent: 'bg-blue-500', WTI: 'bg-cyan-500', RBOB: 'bg-red-500', 'Heating Oil': 'bg-amber-500',
};

export function Analytics() {
  const [panels, setPanels] = useState(INITIAL);
  const [notes, setNotes] = useState(
    '• Brent-WTI arb widening — monitor USGC export economics\n• RBOB cracks firm into driving season; watch refinery turnarounds\n• Crack spreads supportive of refinery runs ahead of driving season\n• Watch DXY breakout for cross-commodity headwind'
  );

  const { data: quotes } = useQuotes('all');
  const corr = useCorrelation();
  const cmp = useComparison();
  const brent = useSeries('brent');
  const spreads = computeSpreads(quotes?.quotes);

  // 30d realized vol from live histories, with a Gas Oil static placeholder.
  const vols = [
    ...ENERGY_ASSETS.map((a) => ({ name: a.label, vol: realizedVol(cmp.byId[a.id]) })).filter((v) => v.vol != null),
    { name: 'Gas Oil', vol: 29.3 },
  ] as { name: string; vol: number }[];

  const renderPanel = (type: string) => {
    switch (type) {
      case 'multiline': return <MultiLineChart data={cmp.data.length ? cmp.data : comparisonSeries} series={['Brent', 'WTI', 'RBOB', 'Heating Oil']} height={200} />;
      case 'area': return <AreaChartPro data={brent.data.length ? brent.data : brentSeries} color="#8b5cf6" height={200} />;
      case 'corr': return <CorrelationHeatmap matrix={corr.matrix ?? correlationMatrix} assets={corr.labels ?? CORRELATION_ASSETS} />;
      case 'spreads': return <SpreadBars data={spreads.map((s) => ({ name: s.name, value: s.value }))} height={200} />;
      default: return null;
    }
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Analytics Workspace"
        description="Quant research · draggable panels · custom layouts"
        status="live"
        actions={
          <>
            <Button variant="outline" size="sm"><LayoutGrid className="h-3.5 w-3.5" />Layouts</Button>
            <Button variant="outline" size="sm"><Plus className="h-3.5 w-3.5" />Add Panel</Button>
            <Button variant="primary" size="sm"><Save className="h-3.5 w-3.5" />Save</Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
        {/* Draggable panel grid */}
        <div className="xl:col-span-3">
          <p className="mb-2 text-[10px] uppercase tracking-widest text-slate-600">Drag panels to rearrange</p>
          <Reorder.Group axis="y" values={panels} onReorder={setPanels} className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {panels.map((panel) => (
              <Reorder.Item key={panel.id} value={panel} className="list-none">
                <motion.div whileDrag={{ scale: 1.02, zIndex: 50 }}>
                  <Card className="h-[280px] flex flex-col">
                    <div className="flex items-center justify-between border-b border-[#1f2230] px-3 py-2">
                      <div className="flex items-center gap-1.5">
                        <GripVertical className="h-3.5 w-3.5 cursor-grab text-slate-600 active:cursor-grabbing" />
                        <span className="text-[12px] font-semibold uppercase tracking-wider text-slate-300">{panel.title}</span>
                      </div>
                    </div>
                    <div className="flex-1 p-3">{renderPanel(panel.type)}</div>
                  </Card>
                </motion.div>
              </Reorder.Item>
            ))}
          </Reorder.Group>
        </div>

        {/* Right rail: notes + vol */}
        <div className="space-y-4">
          <Card className="flex h-[280px] flex-col">
            <CardHeader title="Strategy Notes" subtitle="Desk commentary" />
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="flex-1 resize-none bg-transparent p-3 text-[11px] leading-relaxed text-slate-300 placeholder:text-slate-600 focus:outline-none"
              placeholder="Add your research notes…"
            />
          </Card>
          <Card className="h-[280px] flex flex-col">
            <CardHeader title="Volatility Panel" subtitle="30d realized" />
            <div className="flex-1 space-y-2.5 p-4">
              {vols.map((v) => (
                <div key={v.name}>
                  <div className="mb-1 flex justify-between">
                    <span className="text-[11px] text-slate-300">{v.name}</span>
                    <span className="mono text-[11px] text-slate-200">{v.vol}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-[#1c1e27]">
                    <div className={`h-full rounded-full ${VOL_COLORS[v.name] ?? 'bg-purple-500'}`} style={{ width: `${Math.min(v.vol, 100)}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <MarketMovers />
        <LeadLagAnalysis />
      </div>

      <SpreadMonitor spreads={spreads} />
    </div>
  );
}
