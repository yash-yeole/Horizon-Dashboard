import { type HTMLAttributes, type ReactNode, forwardRef } from 'react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, hover = false, children, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'rounded-lg border border-[#1f2230] bg-[#0f1117] transition-colors',
        hover && 'hover:border-[#2a2d3e] hover:bg-[#11131a]',
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
);
Card.displayName = 'Card';

export function CardHeader({
  title,
  subtitle,
  action,
  icon,
  className,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex items-center justify-between border-b border-[#1f2230] px-4 py-2.5', className)}>
      <div className="flex items-center gap-2 min-w-0">
        {icon && <span className="text-slate-500">{icon}</span>}
        <div className="min-w-0">
          <h3 className="text-[12px] font-semibold uppercase tracking-wider text-slate-300 truncate">{title}</h3>
          {subtitle && <p className="text-[10px] text-slate-500 truncate">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="flex items-center gap-1 shrink-0">{action}</div>}
    </div>
  );
}

export function CardBody({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={cn('p-4', className)}>{children}</div>;
}

// Animated card wrapper for grid fade-ins
export function MotionCard({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
