import { useEffect, useState } from 'react';

export function useClock(): string {
  const [time, setTime] = useState(() => formatUTC());
  useEffect(() => {
    const id = setInterval(() => setTime(formatUTC()), 1000);
    return () => clearInterval(id);
  }, []);
  return time;
}

function formatUTC(): string {
  const d = new Date();
  const h = String(d.getUTCHours()).padStart(2, '0');
  const m = String(d.getUTCMinutes()).padStart(2, '0');
  const s = String(d.getUTCSeconds()).padStart(2, '0');
  return `${h}:${m}:${s}`;
}
