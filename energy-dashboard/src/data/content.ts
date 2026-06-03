import type { NewsItem, InventoryData, FreightRate, WeatherStation, AlertItem } from '@/types';

export const NEWS: NewsItem[] = [
  { id: 'n1', headline: 'OPEC+ signals deeper voluntary cuts into Q3 amid demand concerns', summary: 'Saudi Arabia and Russia indicated willingness to extend production curbs as Chinese demand recovery shows signs of stalling. Analysts see Brent support near $80.', source: 'Reuters', timestamp: '2 min ago', category: 'Crude', sentiment: 'bullish', importance: 'high', tags: ['OPEC', 'Supply', 'Brent'] },
  { id: 'n2', headline: 'RBOB cracks widen as US gasoline stocks draw ahead of driving season', summary: 'EIA weekly report shows a larger-than-expected gasoline inventory draw, lifting front-month RBOB and supporting refining margins.', source: 'Bloomberg', timestamp: '14 min ago', category: 'Products', sentiment: 'bullish', importance: 'high', tags: ['EIA', 'RBOB', 'Cracks'] },
  { id: 'n3', headline: 'Heating Oil firms on tighter distillate supply', summary: 'Low ULSD inventories and steady export demand keep the front of the heating oil curve supported.', source: 'ICIS', timestamp: '28 min ago', category: 'Products', sentiment: 'bullish', importance: 'medium', tags: ['Heating Oil', 'Distillate', 'Supply'] },
  { id: 'n4', headline: 'Gas Oil strengthens as European distillate demand firms', summary: 'ICE Gas Oil gains as refinery turnarounds tighten middle-distillate availability into summer.', source: 'Argus', timestamp: '45 min ago', category: 'Products', sentiment: 'bullish', importance: 'medium', tags: ['Gas Oil', 'Europe', 'Distillate'] },
  { id: 'n5', headline: 'Red Sea diversions keep VLCC rates elevated', summary: 'Continued rerouting around Cape of Good Hope adds tonne-mile demand, supporting dirty tanker earnings.', source: 'Baltic Exchange', timestamp: '1 hr ago', category: 'Freight', sentiment: 'bullish', importance: 'medium', tags: ['VLCC', 'Freight', 'Red Sea'] },
  { id: 'n6', headline: 'Fed minutes show divided committee on rate path', summary: 'Dollar strengthens modestly; commodity complex sees mild headwind from firmer DXY.', source: 'WSJ', timestamp: '1 hr ago', category: 'Macro', sentiment: 'bearish', importance: 'high', tags: ['Fed', 'DXY', 'Rates'] },
  { id: 'n7', headline: 'US refinery utilization climbs to 91.2% ahead of driving season', summary: 'Gulf Coast plants ramp runs, supporting crude demand and gasoline cracks.', source: 'EIA', timestamp: '2 hr ago', category: 'Products', sentiment: 'bullish', importance: 'low', tags: ['Refining', 'Gasoline', 'USGC'] },
  { id: 'n8', headline: 'Cooler weather forecast trims US power burn expectations', summary: 'Updated NOAA models show below-normal temps across Midwest, easing near-term gas demand.', source: 'NOAA', timestamp: '3 hr ago', category: 'Weather', sentiment: 'bearish', importance: 'low', tags: ['Weather', 'Power', 'HDD'] },
];

export const INVENTORIES: InventoryData[] = (() => {
  const data: InventoryData[] = [];
  let crude = 462, gasoline = 230, distillate = 118, propane = 52;
  for (let i = 11; i >= 0; i--) {
    crude += (Math.random() - 0.5) * 8;
    gasoline += (Math.random() - 0.5) * 5;
    distillate += (Math.random() - 0.5) * 4;
    propane += (Math.random() - 0.5) * 3;
    data.push({
      week: `W-${i}`,
      crude: +crude.toFixed(1),
      gasoline: +gasoline.toFixed(1),
      distillate: +distillate.toFixed(1),
      propane: +propane.toFixed(1),
      total: +(crude + gasoline + distillate + propane).toFixed(1),
    });
  }
  return data;
})();

export const FREIGHT_RATES: FreightRate[] = [
  { route: 'AG → China (VLCC)', vessel: 'VLCC', rate: 48250, change: 1850, changePct: 3.99, unit: '$/day' },
  { route: 'WAF → UKC (Suezmax)', vessel: 'Suezmax', rate: 38400, change: -620, changePct: -1.59, unit: '$/day' },
  { route: 'Baltic → UKC (Aframax)', vessel: 'Aframax', rate: 31200, change: 980, changePct: 3.24, unit: '$/day' },
  { route: 'US Gulf → Asia (VLCC)', vessel: 'VLCC', rate: 9.85, change: 0.35, changePct: 3.68, unit: '$/bbl' },
  { route: 'MEG → Japan (LR2)', vessel: 'LR2', rate: 42100, change: -1100, changePct: -2.55, unit: '$/day' },
  { route: 'US → NWE (MR)', vessel: 'MR', rate: 26800, change: 540, changePct: 2.06, unit: '$/day' },
];

export const PORT_CONGESTION = [
  { port: 'Singapore', vessels: 142, waiting: 28, severity: 'high' as const, trend: 'up' as const },
  { port: 'Fujairah', vessels: 89, waiting: 12, severity: 'medium' as const, trend: 'down' as const },
  { port: 'Houston', vessels: 64, waiting: 18, severity: 'medium' as const, trend: 'up' as const },
  { port: 'Rotterdam', vessels: 78, waiting: 9, severity: 'low' as const, trend: 'flat' as const },
  { port: 'Ras Tanura', vessels: 51, waiting: 6, severity: 'low' as const, trend: 'down' as const },
];

export const WEATHER_STATIONS: WeatherStation[] = [
  { city: 'Chicago', region: 'US Midwest', temp: 12, anomaly: -3.2, hdd: 18, cdd: 0, forecast: 'Cooler' },
  { city: 'New York', region: 'US Northeast', temp: 16, anomaly: -1.1, hdd: 9, cdd: 0, forecast: 'Seasonal' },
  { city: 'Houston', region: 'US Gulf', temp: 28, anomaly: 2.4, hdd: 0, cdd: 12, forecast: 'Warmer' },
  { city: 'London', region: 'NW Europe', temp: 11, anomaly: -0.8, hdd: 14, cdd: 0, forecast: 'Seasonal' },
  { city: 'Tokyo', region: 'NE Asia', temp: 22, anomaly: 1.6, hdd: 2, cdd: 6, forecast: 'Warmer' },
  { city: 'Frankfurt', region: 'C Europe', temp: 13, anomaly: -1.9, hdd: 11, cdd: 0, forecast: 'Cooler' },
];

export const ALERTS: AlertItem[] = [
  { id: 'a1', title: 'Brent breaks $82.00', message: 'Brent front-month crossed above key resistance at $82.00/bbl.', type: 'price', severity: 'warning', timestamp: '5 min ago', read: false, commodity: 'Brent' },
  { id: 'a2', title: 'EIA gasoline draw surprise', message: 'Gasoline stocks drew 3.1M bbl vs 1.2M consensus. Bullish for RBOB cracks.', type: 'inventory', severity: 'critical', timestamp: '14 min ago', read: false, commodity: 'RBOB Gasoline' },
  { id: 'a3', title: 'VLCC rates spike', message: 'AG→China VLCC rates up 4% intraday on Red Sea reroute demand.', type: 'freight', severity: 'info', timestamp: '38 min ago', read: false, commodity: 'Freight' },
  { id: 'a4', title: 'Heating Oil volatility elevated', message: 'Heating Oil 30-day realized vol exceeds 30%. Monitor positions.', type: 'price', severity: 'warning', timestamp: '1 hr ago', read: true, commodity: 'Heating Oil' },
  { id: 'a5', title: 'Cold front — US Midwest', message: 'NOAA forecasts below-normal temps; HDD upside risk for gas demand.', type: 'weather', severity: 'info', timestamp: '2 hr ago', read: true, commodity: 'Weather' },
];

export const ECONOMIC_CALENDAR = [
  { time: '13:30', event: 'US EIA Crude Inventories', impact: 'high' as const, forecast: '-1.2M', previous: '+3.6M' },
  { time: '15:00', event: 'US Consumer Confidence', impact: 'medium' as const, forecast: '102.5', previous: '101.3' },
  { time: '08:30', event: 'EU CPI Flash YoY', impact: 'high' as const, forecast: '2.4%', previous: '2.6%' },
  { time: '14:00', event: 'FOMC Member Speech', impact: 'medium' as const, forecast: '—', previous: '—' },
  { time: '10:00', event: 'IEA Monthly Oil Report', impact: 'high' as const, forecast: '—', previous: '—' },
];
