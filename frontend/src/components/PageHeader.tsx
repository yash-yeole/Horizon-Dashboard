import { useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { StatusDot } from '@/components/ui';

/**
 * Renders the page title/status/actions into the top bar (via portal slots
 * #page-chrome-title and #page-chrome-actions) instead of an in-page row, so
 * the chrome lives in the global header and the page body keeps the space.
 */
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
  const [titleEl, setTitleEl] = useState<HTMLElement | null>(null);
  const [actionsEl, setActionsEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    setTitleEl(document.getElementById('page-chrome-title'));
    setActionsEl(document.getElementById('page-chrome-actions'));
  }, []);

  return (
    <>
      {titleEl && createPortal(
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-base font-bold tracking-tight text-slate-100">{title}</h1>
            <StatusDot status={status} label={status === 'live' ? 'Live' : status} />
          </div>
          {description && <p className="truncate text-[10px] text-slate-500">{description}</p>}
        </div>,
        titleEl,
      )}
      {actionsEl && actions && createPortal(actions, actionsEl)}
    </>
  );
}
