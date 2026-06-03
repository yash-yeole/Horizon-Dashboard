import { useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, Info, Bell, Plus, Check, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Tabs, Button } from '@/components/ui';
import { ALERTS } from '@/data/content';
import { cn } from '@/lib/utils';
import type { AlertItem } from '@/types';

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'unread', label: 'Unread' },
  { id: 'critical', label: 'Critical' },
  { id: 'price', label: 'Price' },
  { id: 'news', label: 'News' },
];

export function Alerts() {
  const [filter, setFilter] = useState('all');
  const [alerts, setAlerts] = useState<AlertItem[]>(ALERTS);

  const filtered = alerts.filter((a) => {
    if (filter === 'all') return true;
    if (filter === 'unread') return !a.read;
    if (filter === 'critical') return a.severity === 'critical';
    return a.type === filter;
  });

  const markRead = (id: string) => setAlerts((p) => p.map((a) => (a.id === id ? { ...a, read: true } : a)));
  const remove = (id: string) => setAlerts((p) => p.filter((a) => a.id !== id));

  const icons = { critical: AlertTriangle, warning: AlertTriangle, info: Info };
  const colors = { critical: 'text-red-400 bg-red-500/10', warning: 'text-amber-400 bg-amber-500/10', info: 'text-blue-400 bg-blue-500/10' };
  const sevBadge = { critical: 'red', warning: 'amber', info: 'blue' } as const;

  return (
    <div className="space-y-4">
      <PageHeader
        title="Alerts Center"
        description="Price triggers · news flags · risk notifications"
        status="warning"
        actions={<Button variant="primary" size="sm"><Plus className="h-3.5 w-3.5" />New Alert</Button>}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: 'Total', value: alerts.length, icon: Bell, c: 'text-slate-300' },
          { label: 'Unread', value: alerts.filter((a) => !a.read).length, icon: Bell, c: 'text-blue-400' },
          { label: 'Critical', value: alerts.filter((a) => a.severity === 'critical').length, icon: AlertTriangle, c: 'text-red-400' },
          { label: 'Triggered 24h', value: 12, icon: AlertTriangle, c: 'text-amber-400' },
        ].map((s) => (
          <Card key={s.label} className="flex items-center gap-3 p-3">
            <div className={cn('flex h-9 w-9 items-center justify-center rounded-md bg-[#161820]', s.c)}>
              <s.icon className="h-4 w-4" />
            </div>
            <div>
              <p className="mono text-lg font-bold text-slate-100">{s.value}</p>
              <p className="text-[10px] uppercase tracking-wide text-slate-500">{s.label}</p>
            </div>
          </Card>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <Tabs tabs={FILTERS} value={filter} onChange={setFilter} />
        <Button variant="ghost" size="sm" onClick={() => setAlerts((p) => p.map((a) => ({ ...a, read: true })))}>
          <Check className="h-3.5 w-3.5" />Mark all read
        </Button>
      </div>

      <Card>
        <CardHeader title="Alert Feed" subtitle={`${filtered.length} alerts`} />
        <div className="divide-y divide-[#161820]">
          {filtered.map((a, i) => {
            const Ico = icons[a.severity];
            return (
              <motion.div
                key={a.id}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className={cn('group flex items-center gap-3 px-4 py-3', !a.read && 'bg-blue-500/[0.03]')}
              >
                <div className={cn('flex h-8 w-8 shrink-0 items-center justify-center rounded-md', colors[a.severity])}>
                  <Ico className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-[12px] font-medium text-slate-100">{a.title}</p>
                    <Badge variant={sevBadge[a.severity]}>{a.severity}</Badge>
                    {a.commodity && <Badge variant="neutral">{a.commodity}</Badge>}
                    {!a.read && <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />}
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">{a.message}</p>
                  <p className="mt-0.5 text-[9px] text-slate-600">{a.timestamp}</p>
                </div>
                <div className="flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                  {!a.read && (
                    <button onClick={() => markRead(a.id)} className="flex h-7 w-7 items-center justify-center rounded text-slate-500 hover:bg-[#1c1e27] hover:text-green-400">
                      <Check className="h-3.5 w-3.5" />
                    </button>
                  )}
                  <button onClick={() => remove(a.id)} className="flex h-7 w-7 items-center justify-center rounded text-slate-500 hover:bg-[#1c1e27] hover:text-red-400">
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}
