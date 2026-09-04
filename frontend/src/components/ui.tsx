import { type ReactNode, type ButtonHTMLAttributes, useState } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

/* ---------------- Button ---------------- */
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'ghost' | 'outline' | 'subtle';
  size?: 'sm' | 'md' | 'icon';
}

export function Button({
  variant = 'ghost',
  size = 'md',
  className,
  children,
  ...props
}: ButtonProps) {
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-500',
    ghost: 'text-slate-400 hover:text-slate-100 hover:bg-[#1c1e27]',
    outline: 'border border-[#2a2d3e] text-slate-300 hover:bg-[#1c1e27]',
    subtle: 'bg-[#161820] text-slate-300 hover:bg-[#1c1e27]',
  };
  const sizes = {
    sm: 'h-7 px-2.5 text-[11px]',
    md: 'h-8 px-3 text-xs',
    icon: 'h-8 w-8 justify-center',
  };
  return (
    <button
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md font-medium transition-colors disabled:opacity-50',
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}

/* ---------------- Tabs ---------------- */
export function Tabs({
  tabs,
  value,
  onChange,
  className,
}: {
  tabs: { id: string; label: string }[];
  value: string;
  onChange: (id: string) => void;
  className?: string;
}) {
  return (
    <div className={cn('inline-flex items-center gap-0.5 rounded-md bg-[#0a0b0d] p-0.5 border border-[#1f2230]', className)}>
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            'relative rounded px-2.5 py-1 text-[11px] font-medium transition-colors',
            value === tab.id ? 'text-slate-100' : 'text-slate-500 hover:text-slate-300'
          )}
        >
          {value === tab.id && (
            <motion.div
              layoutId="tab-bg"
              className="absolute inset-0 rounded bg-[#1c1e27]"
              transition={{ type: 'spring', duration: 0.4 }}
            />
          )}
          <span className="relative z-10">{tab.label}</span>
        </button>
      ))}
    </div>
  );
}

/* ---------------- StatusDot ---------------- */
export function StatusDot({
  status,
  label,
}: {
  status: 'live' | 'closed' | 'pre' | 'warning';
  label?: string;
}) {
  const map = {
    live: { color: 'bg-green-400', text: 'text-green-400' },
    closed: { color: 'bg-slate-500', text: 'text-slate-500' },
    pre: { color: 'bg-amber-400', text: 'text-amber-400' },
    warning: { color: 'bg-red-400', text: 'text-red-400' },
  };
  const s = map[status];
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn('h-1.5 w-1.5 rounded-full', s.color, status === 'live' && 'pulse-dot')} />
      {label && <span className={cn('text-[10px] font-medium uppercase tracking-wider', s.text)}>{label}</span>}
    </span>
  );
}

/* ---------------- Skeleton ---------------- */
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton rounded', className)} />;
}

/* ---------------- Tooltip (simple) ---------------- */
export function Tooltip({ content, children }: { content: ReactNode; children: ReactNode }) {
  const [show, setShow] = useState(false);
  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <span className="absolute bottom-full left-1/2 z-50 mb-1.5 -translate-x-1/2 whitespace-nowrap rounded border border-[#2a2d3e] bg-[#161820] px-2 py-1 text-[10px] text-slate-300 shadow-xl">
          {content}
        </span>
      )}
    </span>
  );
}

/* ---------------- Progress ---------------- */
export function Progress({
  value,
  max = 100,
  color = 'bg-blue-500',
  className,
}: {
  value: number;
  max?: number;
  color?: string;
  className?: string;
}) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className={cn('h-1.5 w-full overflow-hidden rounded-full bg-[#1c1e27]', className)}>
      <motion.div
        className={cn('h-full rounded-full', color)}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
      />
    </div>
  );
}

/* ---------------- FilterBar ---------------- */
export function FilterBar({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-wrap items-center gap-2 rounded-lg border border-[#1f2230] bg-[#0f1117] px-3 py-2', className)}>
      {children}
    </div>
  );
}

/* ---------------- SectionTitle ---------------- */
export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-2 flex items-center justify-between">
      <h2 className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">{children}</h2>
      {action}
    </div>
  );
}
