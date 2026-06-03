import type { ReactNode } from 'react';
import { StatusDot } from '@/components/ui';

export function PageHeader({
  title,
  description,
  actions,
  status = 'live',
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  status?: 'live' | 'closed' | 'pre' | 'warning';
}) {
  return (
    <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-lg font-bold tracking-tight text-slate-100">{title}</h1>
          <StatusDot status={status} label={status === 'live' ? 'Live' : status} />
        </div>
        {description && <p className="mt-0.5 text-xs text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
