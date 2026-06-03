import { motion } from 'framer-motion';
import { MapPin } from 'lucide-react';

interface MapPoint {
  x: number; // 0-100 %
  y: number; // 0-100 %
  label: string;
  severity?: 'high' | 'medium' | 'low';
}

export function MapPlaceholder({
  points = [],
  routes = [],
  height = 280,
}: {
  points?: MapPoint[];
  routes?: { x1: number; y1: number; x2: number; y2: number }[];
  height?: number;
}) {
  const sevColor = { high: '#ef4444', medium: '#f59e0b', low: '#10b981' };
  return (
    <div
      className="relative w-full overflow-hidden rounded-md border border-[#1f2230] bg-[#0a0b0d]"
      style={{ height }}
    >
      {/* Grid / graticule */}
      <svg className="absolute inset-0 h-full w-full" preserveAspectRatio="none">
        <defs>
          <pattern id="grid" width="8%" height="14%" patternUnits="userSpaceOnUse">
            <path d="M 100 0 L 0 0 0 100" fill="none" stroke="#1f2230" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" opacity="0.5" />
        {/* Stylized continents (abstract blobs) */}
        <g fill="#11131a" opacity="0.8">
          <ellipse cx="22%" cy="40%" rx="14%" ry="18%" />
          <ellipse cx="50%" cy="55%" rx="10%" ry="14%" />
          <ellipse cx="74%" cy="42%" rx="16%" ry="20%" />
        </g>
        {/* Routes */}
        {routes.map((r, i) => (
          <motion.line
            key={i}
            x1={`${r.x1}%`} y1={`${r.y1}%`} x2={`${r.x2}%`} y2={`${r.y2}%`}
            stroke="#2563eb" strokeWidth="1" strokeDasharray="4 3"
            initial={{ pathLength: 0, opacity: 0 }}
            animate={{ pathLength: 1, opacity: 0.6 }}
            transition={{ duration: 1.2, delay: i * 0.1 }}
          />
        ))}
      </svg>

      {/* Points */}
      {points.map((p, i) => (
        <motion.div
          key={i}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: i * 0.08, type: 'spring' }}
          className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center"
          style={{ left: `${p.x}%`, top: `${p.y}%` }}
        >
          <span className="relative flex h-2.5 w-2.5">
            <span
              className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-60"
              style={{ background: sevColor[p.severity ?? 'low'] }}
            />
            <span
              className="relative inline-flex h-2.5 w-2.5 rounded-full ring-2 ring-[#0a0b0d]"
              style={{ background: sevColor[p.severity ?? 'low'] }}
            />
          </span>
          <span className="mt-1 whitespace-nowrap rounded bg-[#0a0b0d]/80 px-1 text-[8px] text-slate-400">{p.label}</span>
        </motion.div>
      ))}

      <div className="absolute bottom-2 right-2 flex items-center gap-1 rounded bg-[#0a0b0d]/80 px-1.5 py-0.5 text-[8px] text-slate-600">
        <MapPin className="h-2.5 w-2.5" /> Interactive map · placeholder
      </div>
    </div>
  );
}

export type { MapPoint };
