import { AnimatePresence, motion } from 'framer-motion';
import { Bell, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { FiredAlert } from '@/lib/alerts';

export function AlertToasts({ toasts, onDismiss }: { toasts: FiredAlert[]; onDismiss: (id: string) => void }) {
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[100] flex w-72 flex-col gap-2">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 30 }}
            className={cn(
              'pointer-events-auto flex items-start gap-2.5 rounded-lg border bg-[#0f1117] p-3 shadow-2xl',
              t.severity === 'critical' ? 'border-red-500/40' : 'border-amber-500/40',
            )}
          >
            <Bell className={cn('mt-0.5 h-4 w-4 shrink-0', t.severity === 'critical' ? 'text-red-400' : 'text-amber-400')} />
            <div className="min-w-0 flex-1">
              <p className="text-[12px] font-semibold text-slate-100">Alert triggered</p>
              <p className="text-[11px] font-medium text-slate-300">{t.title}</p>
              <p className="mt-0.5 text-[10px] text-slate-500">{t.message}</p>
            </div>
            <button onClick={() => onDismiss(t.id)} className="text-slate-600 hover:text-slate-300">
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
