import { NavLink } from 'react-router-dom';
import { motion } from 'framer-motion';
import * as Icons from 'lucide-react';
import { NAV_ITEMS } from '@/constants';
import { useUIStore } from '@/store/useUIStore';
import { cn } from '@/lib/utils';
import { Tooltip } from '@/components/ui';

function Icon({ name, className }: { name: string; className?: string }) {
  const Cmp = (Icons as unknown as Record<string, Icons.LucideIcon>)[name] ?? Icons.Circle;
  return <Cmp className={className} strokeWidth={1.75} />;
}

export function Sidebar() {
  const collapsed = useUIStore((s) => s.sidebarCollapsed);
  const toggle = useUIStore((s) => s.toggleSidebar);

  return (
    <motion.aside
      animate={{ width: collapsed ? 56 : 208 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="relative z-30 flex h-screen flex-col border-r border-[#1f2230] bg-[#0a0b0d]"
    >
      {/* Brand */}
      <div className="flex h-12 items-center gap-2.5 border-b border-[#1f2230] px-3.5">
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-blue-600 to-cyan-500">
          <Icons.Zap className="h-4 w-4 text-white" strokeWidth={2.25} />
        </div>
        {!collapsed && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-w-0">
            <p className="text-[13px] font-bold leading-tight text-slate-100">HORIZON</p>
            <p className="text-[9px] uppercase tracking-widest text-slate-500">Energy Terminal</p>
          </motion.div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <div className="space-y-0.5">
          {NAV_ITEMS.map((item) => {
            const content = (
              <NavLink
                key={item.id}
                to={item.path}
                end={item.path === '/'}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center gap-3 rounded-md px-2.5 py-2 text-[12px] font-medium transition-colors',
                    isActive
                      ? 'text-slate-100'
                      : 'text-slate-500 hover:bg-[#161820] hover:text-slate-200'
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <motion.div
                        layoutId="active-nav"
                        className="absolute inset-0 rounded-md bg-blue-600/10 ring-1 ring-inset ring-blue-500/20"
                        transition={{ type: 'spring', duration: 0.4 }}
                      />
                    )}
                    {isActive && (
                      <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r bg-blue-500" />
                    )}
                    <Icon name={item.icon} className={cn('relative z-10 h-4 w-4 shrink-0', isActive && 'text-blue-400')} />
                    {!collapsed && (
                      <span className="relative z-10 flex-1 truncate">{item.label}</span>
                    )}
                    {!collapsed && 'badge' in item && item.badge && (
                      <span className="relative z-10 rounded bg-red-500/15 px-1.5 py-0.5 text-[9px] font-bold text-red-400">
                        {item.badge}
                      </span>
                    )}
                  </>
                )}
              </NavLink>
            );
            return collapsed ? (
              <Tooltip key={item.id} content={item.label}>
                <div className="w-full">{content}</div>
              </Tooltip>
            ) : (
              content
            );
          })}
        </div>
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-[#1f2230] p-2">
        <button
          onClick={toggle}
          className="flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-[11px] text-slate-500 transition-colors hover:bg-[#161820] hover:text-slate-300"
        >
          <Icons.PanelLeftClose
            className={cn('h-4 w-4 shrink-0 transition-transform', collapsed && 'rotate-180')}
            strokeWidth={1.75}
          />
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </motion.aside>
  );
}
