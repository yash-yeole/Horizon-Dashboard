import { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Card, CardHeader } from '@/components/ui/Card';
import { Wifi, WifiOff } from 'lucide-react';
import { useShippingVessels, useShippingChokepoints } from '@/hooks/useQuotes';
import { cn } from '@/lib/utils';
import type { AisVessel } from '@/types/api';

type Mode = 'heatmap' | 'tankers' | 'routes';

// Free, keyless dark basemap (CARTO raster tiles); glyphs for cluster labels.
const STYLE: maplibregl.StyleSpecification = {
  version: 8,
  glyphs: 'https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf',
  sources: {
    carto: {
      type: 'raster',
      tiles: [
        'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
        'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      ],
      tileSize: 256,
      attribution: '© OpenStreetMap © CARTO',
    },
  },
  layers: [{ id: 'carto', type: 'raster', source: 'carto' }],
};

const EMPTY: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

function toGeoJSON(vessels: AisVessel[]): GeoJSON.FeatureCollection {
  return {
    type: 'FeatureCollection',
    features: vessels.map((v) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [v.lon, v.lat] },
      properties: {
        name: v.name, klass: v.klass, sog: v.sog ?? '—', heading: v.heading ?? '—',
        dest: v.destination, lastSeen: v.lastSeen,
      },
    })),
  };
}

const STATUS_COLOR: Record<string, string> = {
  Normal: 'text-green-400', Elevated: 'text-amber-400', Congested: 'text-red-400',
};

export function TankerMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const loadedRef = useRef(false);
  const [mode, setMode] = useState<Mode>('heatmap');

  const { data: vesselData } = useShippingVessels();
  const { data: chokeData } = useShippingChokepoints();
  const vessels = vesselData?.vessels ?? [];
  const status = vesselData?.status ?? chokeData?.status;
  const live = !!status?.connected;
  const offlineMsg = !status?.hasKey ? 'AIS feed offline — add an aisstream.io key' : 'Connecting to AIS feed…';

  // init map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE,
      center: [40, 20],
      zoom: 1.2,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.on('load', () => {
      map.addSource('heat', { type: 'geojson', data: EMPTY });
      map.addSource('pts', { type: 'geojson', data: EMPTY, cluster: true, clusterRadius: 45, clusterMaxZoom: 7 });

      map.addLayer({
        id: 'heat', type: 'heatmap', source: 'heat',
        paint: {
          'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 8, 6, 30],
          'heatmap-intensity': 0.9,
          'heatmap-opacity': 0.85,
          'heatmap-color': [
            'interpolate', ['linear'], ['heatmap-density'],
            0, 'rgba(0,0,0,0)', 0.2, '#0ea5e9', 0.4, '#22d3ee', 0.6, '#facc15', 0.8, '#fb923c', 1, '#ef4444',
          ],
        },
      });
      map.addLayer({
        id: 'clusters', type: 'circle', source: 'pts', filter: ['has', 'point_count'],
        layout: { visibility: 'none' },
        paint: {
          'circle-color': '#0e7490', 'circle-opacity': 0.7,
          'circle-radius': ['step', ['get', 'point_count'], 12, 20, 18, 100, 26],
          'circle-stroke-width': 1, 'circle-stroke-color': '#22d3ee',
        },
      });
      map.addLayer({
        id: 'cluster-count', type: 'symbol', source: 'pts', filter: ['has', 'point_count'],
        layout: { visibility: 'none', 'text-field': '{point_count_abbreviated}', 'text-size': 11 },
        paint: { 'text-color': '#e2e8f0' },
      });
      map.addLayer({
        id: 'points', type: 'circle', source: 'pts', filter: ['!', ['has', 'point_count']],
        layout: { visibility: 'none' },
        paint: { 'circle-radius': 4, 'circle-color': '#22d3ee', 'circle-stroke-width': 1, 'circle-stroke-color': '#0a0b0d' },
      });

      const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, className: 'tanker-popup' });
      map.on('mouseenter', 'points', (e) => {
        map.getCanvas().style.cursor = 'pointer';
        const f = e.features?.[0];
        if (!f) return;
        const p = f.properties as Record<string, unknown>;
        const t = p.lastSeen ? new Date(Number(p.lastSeen) * 1000).toLocaleTimeString() : '—';
        popup.setLngLat((f.geometry as GeoJSON.Point).coordinates as [number, number]).setHTML(
          `<div style="font-size:11px;line-height:1.4">
             <b>${p.name}</b><br/>${p.klass} · ${p.sog} kn · hdg ${p.heading}°<br/>
             <span style="color:#94a3b8">${p.dest ? 'to ' + p.dest + ' · ' : ''}${t}</span>
           </div>`,
        ).addTo(map);
      });
      map.on('mouseleave', 'points', () => { map.getCanvas().style.cursor = ''; popup.remove(); });

      loadedRef.current = true;
      const src = map.getSource('heat') as maplibregl.GeoJSONSource | undefined;
      if (src && pendingRef.current) { src.setData(pendingRef.current); (map.getSource('pts') as maplibregl.GeoJSONSource).setData(pendingRef.current); }
      applyMode(map, mode);
    });

    return () => { map.remove(); mapRef.current = null; loadedRef.current = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // push vessel data into the sources
  const pendingRef = useRef<GeoJSON.FeatureCollection | null>(null);
  useEffect(() => {
    const fc = toGeoJSON(vessels);
    pendingRef.current = fc;
    const map = mapRef.current;
    if (map && loadedRef.current) {
      (map.getSource('heat') as maplibregl.GeoJSONSource | undefined)?.setData(fc);
      (map.getSource('pts') as maplibregl.GeoJSONSource | undefined)?.setData(fc);
    }
  }, [vessels]);

  // mode → layer visibility
  useEffect(() => {
    const map = mapRef.current;
    if (map && loadedRef.current) applyMode(map, mode);
  }, [mode]);

  return (
    <Card className="flex flex-col">
      <CardHeader
        title="Global Tanker Intelligence"
        subtitle={`AIS · ${status?.vesselCount ?? 0} tankers tracked`}
        action={
          <span className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wider">
            {live ? <><Wifi className="h-3.5 w-3.5 text-green-400" /><span className="text-green-400">Live</span></>
                  : <><WifiOff className="h-3.5 w-3.5 text-amber-400" /><span className="text-amber-400">Offline</span></>}
          </span>
        }
      />
      <div className="flex items-center gap-1.5 px-3 pt-2">
        {(['heatmap', 'tankers', 'routes'] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            disabled={m === 'routes'}
            className={cn(
              'rounded-md px-2.5 py-1 text-[11px] font-medium capitalize transition-colors',
              mode === m ? 'bg-cyan-500/15 text-cyan-300' : 'text-slate-400 hover:text-slate-200',
              m === 'routes' && 'cursor-not-allowed opacity-40',
            )}
          >
            {m}{m === 'routes' ? ' (soon)' : ''}
          </button>
        ))}
      </div>
      <div className="relative p-3">
        <div ref={containerRef} className="h-[320px] w-full overflow-hidden rounded-md" />
        {!live && (
          <div className="pointer-events-none absolute inset-3 flex items-center justify-center rounded-md bg-[#0a0b0d]/60">
            <span className="rounded-md border border-[#1f2230] bg-[#0f1117] px-3 py-1.5 text-[11px] text-amber-300">{offlineMsg}</span>
          </div>
        )}
      </div>
      {/* Chokepoint strip */}
      <div className="grid grid-cols-5 gap-2 border-t border-[#161820] p-3">
        {(chokeData?.chokepoints ?? []).map((c) => (
          <div key={c.name} className="rounded-md border border-[#1f2230] bg-[#0a0b0d]/50 p-2 text-center">
            <p className="truncate text-[9px] uppercase tracking-wide text-slate-500" title={c.name}>{c.name}</p>
            <p className="mono text-sm font-semibold text-slate-100">{c.count}</p>
            <p className={cn('text-[9px] font-medium', STATUS_COLOR[c.status] ?? 'text-slate-400')}>{c.status}</p>
          </div>
        ))}
      </div>
    </Card>
  );
}

function applyMode(map: maplibregl.Map, mode: Mode) {
  const show = (id: string, v: boolean) => map.getLayer(id) && map.setLayoutProperty(id, 'visibility', v ? 'visible' : 'none');
  show('heat', mode === 'heatmap');
  show('clusters', mode === 'tankers');
  show('cluster-count', mode === 'tankers');
  show('points', mode === 'tankers');
}
