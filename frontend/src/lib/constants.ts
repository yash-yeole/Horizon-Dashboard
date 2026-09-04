export const COLORS = {
  background: '#0a0b0d',
  surface: '#0f1117',
  surface2: '#161820',
  surface3: '#1c1e27',
  border: '#1f2230',
  borderStrong: '#2a2d3e',
  accent: '#2563eb',
  green: '#10b981',
  red: '#ef4444',
  amber: '#f59e0b',
  blue: '#3b82f6',
  purple: '#8b5cf6',
  cyan: '#06b6d4',
  textPrimary: '#e2e8f0',
  textSecondary: '#94a3b8',
  textMuted: '#475569',
} as const;

export const CHART_COLORS = [
  '#2563eb',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#06b6d4',
  '#ec4899',
  '#14b8a6',
];

export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', path: '/', icon: 'LayoutDashboard' },
  { id: 'crude', label: 'Crude Oil', path: '/crude', icon: 'Droplets' },
  { id: 'products', label: 'Products', path: '/products', icon: 'Fuel' },
  { id: 'freight', label: 'Freight', path: '/freight', icon: 'Anchor' },
  { id: 'macro', label: 'Macro', path: '/macro', icon: 'TrendingUp' },
  { id: 'weather', label: 'Weather', path: '/weather', icon: 'CloudSun' },
  { id: 'inventories', label: 'Inventories', path: '/inventories', icon: 'Database' },
  { id: 'news', label: 'News', path: '/news', icon: 'Newspaper' },
  { id: 'analytics', label: 'Analytics', path: '/analytics', icon: 'BarChart3' },
  { id: 'paper', label: 'Paper Trading', path: '/paper', icon: 'CandlestickChart' },
  { id: 'alerts', label: 'Alerts', path: '/alerts', icon: 'Bell', badge: 4 },
  { id: 'settings', label: 'Settings', path: '/settings', icon: 'Settings' },
] as const;

export const MARKET_HOURS = {
  ICE: '08:00 - 18:00 UTC',
  NYMEX: '13:30 - 20:00 UTC',
  CME: '13:30 - 20:00 UTC',
};
