import { AnimatePresence, motion } from 'framer-motion';
import { X, Clock, ExternalLink, Tag } from 'lucide-react';
import { SentimentBadge, ImportanceBadge, Badge } from '@/components/ui/Badge';
import { useNews } from '@/hooks/useQuotes';

export function NewsModal({ newsId, onClose }: { newsId: string | null; onClose: () => void }) {
  const { items } = useNews();
  const item = items.find((n) => n.id === newsId);
  return (
    <AnimatePresence>
      {item && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ type: 'spring', duration: 0.3 }}
            onClick={(e) => e.stopPropagation()}
            className="w-full max-w-2xl overflow-hidden rounded-lg border border-[#2a2d3e] bg-[#0f1117] shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-[#1f2230] px-4 py-3">
              <div className="flex items-center gap-2">
                <SentimentBadge sentiment={item.sentiment} />
                <ImportanceBadge importance={item.importance} />
                <Badge variant="blue">{item.category}</Badge>
              </div>
              <button onClick={onClose} className="flex h-7 w-7 items-center justify-center rounded text-slate-500 hover:bg-[#1c1e27] hover:text-slate-200">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-5">
              <div className="mb-2 flex items-center gap-2 text-[10px] text-slate-500">
                <span className="font-semibold text-slate-400">{item.source}</span>
                <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{item.timestamp}</span>
              </div>
              <h2 className="text-base font-semibold leading-snug text-slate-100">{item.headline}</h2>
              <p className="mt-3 text-[13px] leading-relaxed text-slate-400">{item.summary}</p>
              <p className="mt-3 text-[13px] leading-relaxed text-slate-500">
                Market participants are monitoring developments closely as positioning adjusts to the evolving
                supply-demand balance. Desk commentary suggests near-term volatility may remain elevated as
                liquidity thins ahead of the settlement window.
              </p>
              <div className="mt-4 flex flex-wrap items-center gap-1.5">
                <Tag className="h-3 w-3 text-slate-600" />
                {item.tags.map((t) => (
                  <span key={t} className="rounded bg-[#161820] px-2 py-0.5 text-[10px] text-slate-400">{t}</span>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between border-t border-[#1f2230] px-4 py-3">
              <span className="text-[10px] text-slate-600">Source: {item.source} · Energy Wire</span>
              {item.link ? (
                <a
                  href={item.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-[11px] font-medium text-white hover:bg-blue-500"
                >
                  Open full article <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                <button disabled className="flex items-center gap-1.5 rounded-md bg-[#1c1e27] px-3 py-1.5 text-[11px] font-medium text-slate-500">
                  No link <ExternalLink className="h-3 w-3" />
                </button>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
