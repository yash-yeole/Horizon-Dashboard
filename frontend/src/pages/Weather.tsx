import { PageHeader } from '@/components/PageHeader';
import { ChartCard } from '@/components/ChartCard';
import { Card, CardHeader } from '@/components/Card';
import { MapPlaceholder } from '@/components/MapPlaceholder';
import { Badge } from '@/components/Badge';
import { BarChartPro } from '@/components/charts';
import { WEATHER_STATIONS } from '@/data/content';
import { generateTimeSeries, cn } from '@/lib/utils';
import { Thermometer, Wind, CloudRain } from 'lucide-react';

const STORM_POINTS = [
  { x: 74, y: 45, label: 'TS Aletta', severity: 'high' as const },
  { x: 30, y: 38, label: 'Front', severity: 'medium' as const },
  { x: 50, y: 62, label: 'Low', severity: 'low' as const },
];

const hddSeries = generateTimeSeries(15, 30, 0.2).map((d) => ({ time: d.time, value: Math.max(0, +d.value.toFixed(0)) }));

export function Weather() {
  return (
    <div className="space-y-4">
      <PageHeader title="Weather Intelligence" description="Temperature anomalies · HDD/CDD · storm tracking" />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {WEATHER_STATIONS.map((w) => (
          <Card key={w.city} hover className="p-3">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-200">{w.city}</span>
              <Thermometer className={cn('h-3.5 w-3.5', w.anomaly >= 0 ? 'text-red-400' : 'text-blue-400')} />
            </div>
            <p className="text-[9px] text-slate-600">{w.region}</p>
            <p className="mono mt-2 text-lg font-semibold text-slate-100">{w.temp}°C</p>
            <p className={cn('mono text-[10px]', w.anomaly >= 0 ? 'text-red-400' : 'text-blue-400')}>
              {w.anomaly >= 0 ? '+' : ''}{w.anomaly}° anomaly
            </p>
            <div className="mt-2 flex items-center justify-between border-t border-[#1f2230] pt-2 text-[9px] text-slate-500">
              <span>HDD {w.hdd}</span><span>CDD {w.cdd}</span>
            </div>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader title="Storm Tracker" subtitle="Active systems · severity placeholder" action={<Badge variant="red" dot>3 active</Badge>} />
            <div className="p-3"><MapPlaceholder points={STORM_POINTS} height={300} /></div>
          </Card>
        </div>
        <Card className="flex flex-col">
          <CardHeader title="Impact Severity" subtitle="Demand-weighted regions" />
          <div className="flex-1 divide-y divide-[#161820]">
            {[
              { r: 'US Midwest', s: 'High', i: 'Heating demand spike', icon: Wind, c: 'red' as const },
              { r: 'NE Asia', s: 'Medium', i: 'Cooling uptick', icon: Thermometer, c: 'amber' as const },
              { r: 'NW Europe', s: 'Low', i: 'Seasonal norms', icon: CloudRain, c: 'green' as const },
              { r: 'US Gulf', s: 'Medium', i: 'Storm risk', icon: Wind, c: 'amber' as const },
            ].map((row) => (
              <div key={row.r} className="flex items-center gap-3 px-4 py-3">
                <row.icon className="h-4 w-4 text-slate-500" />
                <div className="flex-1">
                  <p className="text-[12px] font-medium text-slate-200">{row.r}</p>
                  <p className="text-[10px] text-slate-500">{row.i}</p>
                </div>
                <Badge variant={row.c} dot>{row.s}</Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="h-[280px]">
          <ChartCard title="Heating Degree Days" subtitle="US population-weighted · HDD" defaultRange="1M">
            <BarChartPro data={hddSeries} color="#3b82f6" height={200} />
          </ChartCard>
        </div>
        <div className="h-[280px]">
          <ChartCard title="Cooling Degree Days" subtitle="US population-weighted · CDD" defaultRange="1M">
            <BarChartPro data={hddSeries.map((d) => ({ ...d, value: Math.max(0, 20 - d.value) }))} color="#f59e0b" height={200} />
          </ChartCard>
        </div>
      </div>
    </div>
  );
}
