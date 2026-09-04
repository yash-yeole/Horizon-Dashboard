import type { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { labelFromImpact, labelVariant } from '@/lib/sentiment';

type Variant = 'green' | 'red' | 'amber' | 'blue' | 'purple' | 'cyan' | 'neutral';

const variantStyles: Record<Variant, string> = {
  green: 'bg-green-500/10 text-green-400 border-green-500/20',
  red: 'bg-red-500/10 text-red-400 border-red-500/20',
  amber: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  blue: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  purple: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  neutral: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
};

export function Badge({
  children,
  variant = 'neutral',
  className,
  dot = false,
}: {
  children: ReactNode;
  variant?: Variant;
  className?: string;
  dot?: boolean;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide',
        variantStyles[variant],
        className
      )}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" />}
      {children}
    </span>
  );
}

export function SentimentBadge({ sentiment }: { sentiment: 'bullish' | 'bearish' | 'neutral' }) {
  const map = {
    bullish: { v: 'green' as const, label: 'Bullish' },
    bearish: { v: 'red' as const, label: 'Bearish' },
    neutral: { v: 'neutral' as const, label: 'Neutral' },
  };
  const { v, label } = map[sentiment];
  return <Badge variant={v}>{label}</Badge>;
}

export function ImpactBadge({ impact }: { impact?: number }) {
  const label = labelFromImpact(impact ?? 0);
  return <Badge variant={labelVariant(label)}>{label}</Badge>;
}

export function ThemeBadge({ theme }: { theme?: string }) {
  if (!theme) return null;
  return <Badge variant="blue">{theme}</Badge>;
}

export function KindBadge({ kind }: { kind?: string }) {
  if (!kind || kind === 'event') return null;
  return <Badge variant="purple">{kind}</Badge>;
}

export function ImportanceBadge({ importance }: { importance: 'high' | 'medium' | 'low' }) {
  const map = {
    high: { v: 'red' as const, label: 'High' },
    medium: { v: 'amber' as const, label: 'Med' },
    low: { v: 'neutral' as const, label: 'Low' },
  };
  const { v, label } = map[importance];
  return <Badge variant={v} dot>{label}</Badge>;
}
