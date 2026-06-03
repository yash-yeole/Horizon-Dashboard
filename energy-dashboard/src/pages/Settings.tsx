import { useState } from 'react';
import { User, Bell, Palette, Globe, Shield, Database } from 'lucide-react';
import { PageHeader } from '@/components/widgets/PageHeader';
import { Card, CardHeader } from '@/components/ui/Card';
import { Button } from '@/components/ui';
import { cn } from '@/lib/utils';

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!enabled)}
      className={cn('relative h-5 w-9 rounded-full transition-colors', enabled ? 'bg-blue-600' : 'bg-[#2a2d3e]')}
    >
      <span className={cn('absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform', enabled ? 'translate-x-4' : 'translate-x-0.5')} />
    </button>
  );
}

function Row({ label, desc, children }: { label: string; desc: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 px-4 py-3">
      <div>
        <p className="text-[12px] font-medium text-slate-200">{label}</p>
        <p className="text-[10px] text-slate-500">{desc}</p>
      </div>
      {children}
    </div>
  );
}

const TABS = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'appearance', label: 'Appearance', icon: Palette },
  { id: 'data', label: 'Data Sources', icon: Database },
  { id: 'regional', label: 'Regional', icon: Globe },
  { id: 'security', label: 'Security', icon: Shield },
];

export function Settings() {
  const [tab, setTab] = useState('profile');
  const [toggles, setToggles] = useState({
    priceAlerts: true, newsAlerts: true, email: false, sound: true,
    compact: true, animations: true, realtime: true,
  });
  const set = (k: keyof typeof toggles) => (v: boolean) => setToggles((p) => ({ ...p, [k]: v }));

  return (
    <div className="space-y-4">
      <PageHeader title="Settings" description="Workspace preferences · data · notifications" status="closed" />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        {/* Settings nav */}
        <Card className="h-fit p-2">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                'flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-[12px] font-medium transition-colors',
                tab === t.id ? 'bg-blue-600/10 text-blue-400' : 'text-slate-400 hover:bg-[#161820] hover:text-slate-200'
              )}
            >
              <t.icon className="h-4 w-4" />
              {t.label}
            </button>
          ))}
        </Card>

        {/* Settings content */}
        <div className="space-y-4 lg:col-span-3">
          {tab === 'profile' && (
            <Card>
              <CardHeader title="Profile" subtitle="Account information" />
              <div className="space-y-4 p-4">
                <div className="flex items-center gap-4">
                  <div className="flex h-16 w-16 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 text-xl font-bold text-white">YY</div>
                  <div>
                    <p className="text-sm font-semibold text-slate-100">Yash Y</p>
                    <p className="text-[11px] text-slate-500">Quantitative Analyst · Energy Desk</p>
                    <Button variant="outline" size="sm" className="mt-2">Change avatar</Button>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { l: 'Full Name', v: 'Yash Y' },
                    { l: 'Email', v: 'sakshiyeole210@gmail.com' },
                    { l: 'Desk', v: 'Energy Quant' },
                    { l: 'Timezone', v: 'UTC' },
                  ].map((f) => (
                    <div key={f.l}>
                      <label className="text-[10px] uppercase tracking-wide text-slate-500">{f.l}</label>
                      <input defaultValue={f.v} className="mt-1 h-8 w-full rounded border border-[#1f2230] bg-[#0a0b0d] px-2.5 text-[12px] text-slate-200 focus:border-blue-500/40 focus:outline-none" />
                    </div>
                  ))}
                </div>
              </div>
            </Card>
          )}

          {tab === 'notifications' && (
            <Card>
              <CardHeader title="Notifications" subtitle="Alert delivery preferences" />
              <div className="divide-y divide-[#161820]">
                <Row label="Price Alerts" desc="Trigger on threshold breaches"><Toggle enabled={toggles.priceAlerts} onChange={set('priceAlerts')} /></Row>
                <Row label="News Alerts" desc="High-importance market news"><Toggle enabled={toggles.newsAlerts} onChange={set('newsAlerts')} /></Row>
                <Row label="Email Digest" desc="Daily summary at 06:00 UTC"><Toggle enabled={toggles.email} onChange={set('email')} /></Row>
                <Row label="Sound" desc="Audio cue on critical alerts"><Toggle enabled={toggles.sound} onChange={set('sound')} /></Row>
              </div>
            </Card>
          )}

          {tab === 'appearance' && (
            <Card>
              <CardHeader title="Appearance" subtitle="Theme & density" />
              <div className="divide-y divide-[#161820]">
                <Row label="Compact Density" desc="Tighter spacing for more data"><Toggle enabled={toggles.compact} onChange={set('compact')} /></Row>
                <Row label="Animations" desc="Motion & transitions"><Toggle enabled={toggles.animations} onChange={set('animations')} /></Row>
                <div className="px-4 py-3">
                  <p className="mb-2 text-[12px] font-medium text-slate-200">Accent Color</p>
                  <div className="flex gap-2">
                    {['#2563eb', '#10b981', '#8b5cf6', '#f59e0b', '#06b6d4'].map((c) => (
                      <button key={c} className="h-7 w-7 rounded-full ring-2 ring-offset-2 ring-offset-[#0f1117] transition-transform hover:scale-110" style={{ background: c, '--tw-ring-color': c } as React.CSSProperties} />
                    ))}
                  </div>
                </div>
              </div>
            </Card>
          )}

          {tab === 'data' && (
            <Card>
              <CardHeader title="Data Sources" subtitle="Feed connections" />
              <div className="divide-y divide-[#161820]">
                <Row label="Real-time Feed" desc="ICE / NYMEX / CME live data"><Toggle enabled={toggles.realtime} onChange={set('realtime')} /></Row>
                {['ICE Endex', 'NYMEX', 'Platts', 'Argus', 'EIA', 'Baltic Exchange'].map((s) => (
                  <Row key={s} label={s} desc="Connected · last sync 2s ago">
                    <span className="flex items-center gap-1.5 text-[10px] font-medium uppercase text-green-400"><span className="h-1.5 w-1.5 rounded-full bg-green-400 pulse-dot" />Active</span>
                  </Row>
                ))}
              </div>
            </Card>
          )}

          {(tab === 'regional' || tab === 'security') && (
            <Card>
              <CardHeader title={tab === 'regional' ? 'Regional' : 'Security'} subtitle="Configuration" />
              <div className="p-8 text-center text-[12px] text-slate-500">
                {tab === 'regional' ? 'Locale, timezone, and unit preferences.' : 'Two-factor authentication, sessions, and API keys.'}
              </div>
            </Card>
          )}

          <div className="flex justify-end gap-2">
            <Button variant="outline" size="sm">Cancel</Button>
            <Button variant="primary" size="sm">Save Changes</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
