import {
  AreaChart, Area, LineChart, Line, BarChart, Bar, ComposedChart,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
  ReferenceLine,
} from 'recharts';
import { CHART_COLORS } from '@/lib/constants';
import { ChartTooltip } from './ChartTooltip';

const axisProps = {
  tick: { fill: '#475569', fontSize: 10 },
  axisLine: { stroke: '#1f2230' },
  tickLine: false,
};

/* ---------------- Sparkline ---------------- */
export function Sparkline({
  data,
  color = '#10b981',
  height = 32,
}: {
  data: number[];
  color?: string;
  height?: number;
}) {
  const chartData = data.map((v, i) => ({ i, v }));
  const id = `spark-${color.replace('#', '')}`;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 2, right: 0, bottom: 2, left: 0 }}>
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} fill={`url(#${id})`} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ---------------- Area Chart ---------------- */
export function AreaChartPro({
  data,
  dataKey = 'value',
  color = '#2563eb',
  height = 240,
}: {
  data: Array<Record<string, number | string>>;
  dataKey?: string;
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <defs>
          <linearGradient id={`area-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
        <XAxis dataKey="time" {...axisProps} minTickGap={40} />
        <YAxis {...axisProps} domain={['auto', 'auto']} width={48} />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2d3e', strokeWidth: 1 }} />
        <Area type="monotone" dataKey={dataKey} stroke={color} strokeWidth={1.75} fill={`url(#area-${dataKey})`} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/* ---------------- Multi Line Comparison ---------------- */
export function MultiLineChart({
  data,
  series,
  height = 260,
}: {
  data: Array<Record<string, number | string>>;
  series: string[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
        <XAxis dataKey="time" {...axisProps} minTickGap={40} />
        <YAxis {...axisProps} domain={['auto', 'auto']} width={48} />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2d3e' }} />
        <Legend
          iconType="plainline"
          wrapperStyle={{ fontSize: 10, paddingTop: 8 }}
          formatter={(v) => <span className="text-slate-400">{v}</span>}
        />
        {series.map((s, i) => (
          <Line key={s} type="monotone" dataKey={s} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={1.5} dot={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

/* ---------------- Curve Chart (forward curve) ---------------- */
export function CurveChart({
  data,
  height = 240,
}: {
  data: Array<{ month: string; price: number; previousPrice: number }>;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
        <XAxis dataKey="month" {...axisProps} />
        <YAxis {...axisProps} domain={['auto', 'auto']} width={48} />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#2a2d3e' }} />
        <Legend iconType="plainline" wrapperStyle={{ fontSize: 10, paddingTop: 8 }} formatter={(v) => <span className="text-slate-400">{v}</span>} />
        <Line type="monotone" name="Current" dataKey="price" stroke="#2563eb" strokeWidth={2} dot={{ r: 2.5, fill: '#2563eb' }} />
        <Line type="monotone" name="Prior" dataKey="previousPrice" stroke="#475569" strokeWidth={1.25} strokeDasharray="4 3" dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}

/* ---------------- Volume + Price Composed ---------------- */
export function VolumeChart({
  data,
  height = 240,
}: {
  data: Array<{ time: string; value: number; price: number }>;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
        <XAxis dataKey="time" {...axisProps} minTickGap={30} />
        <YAxis yAxisId="left" {...axisProps} width={40} />
        <YAxis yAxisId="right" orientation="right" {...axisProps} width={40} domain={['auto', 'auto']} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(42,45,62,0.3)' }} />
        <Bar yAxisId="left" dataKey="value" name="Volume" fill="#1d4ed8" opacity={0.4} radius={[2, 2, 0, 0]} />
        <Line yAxisId="right" type="monotone" dataKey="price" name="Price" stroke="#10b981" strokeWidth={1.5} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

/* ---------------- Spread Bar Chart ---------------- */
export function SpreadBars({
  data,
  height = 200,
}: {
  data: Array<{ name: string; value: number }>;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" horizontal={false} />
        <XAxis type="number" {...axisProps} />
        <YAxis type="category" dataKey="name" {...axisProps} width={90} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(42,45,62,0.3)' }} />
        <ReferenceLine x={0} stroke="#2a2d3e" />
        <Bar dataKey="value" radius={[0, 2, 2, 0]}>
          {data.map((d, i) => (
            <Cell key={i} fill={d.value >= 0 ? '#10b981' : '#ef4444'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ---------------- Bar Chart (generic) ---------------- */
export function BarChartPro({
  data,
  dataKey = 'value',
  color = '#2563eb',
  height = 240,
}: {
  data: Array<Record<string, number | string>>;
  dataKey?: string;
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid strokeDasharray="2 4" stroke="#1f2230" vertical={false} />
        <XAxis dataKey="time" {...axisProps} minTickGap={20} />
        <YAxis {...axisProps} width={44} />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'rgba(42,45,62,0.3)' }} />
        <Bar dataKey={dataKey} fill={color} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
