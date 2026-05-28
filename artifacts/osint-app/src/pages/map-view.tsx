import { Layout } from "@/components/layout";
import { EventDrawer } from "@/components/event-drawer";
import { useListEvents } from "@workspace/api-client-react";
import { useState, useMemo, useCallback } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import {
  SIDE_HEX_COLORS, SIDE_COLORS, SIDE_LABELS_EN, SIDE_TEXT_COLORS,
  CATEGORY_COLORS, CATEGORIES, CONFIDENCE_LEVEL_COLORS, CONFIDENCE_LEVEL_LABELS,
} from "@/lib/constants";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Loader2, Radio, X, MapPin, Flame, ShieldAlert } from "lucide-react";
import { useLiveEvents } from "@/hooks/use-live-events";
import type { EventResponse } from "@workspace/api-client-react";

const SIDES = ["red", "blue", "neutral"] as const;
type Side = typeof SIDES[number];

function LiveEventFlyTo({ event }: { event: EventResponse | null }) {
  const map = useMap();
  if (event?.lat && event?.lng) {
    map.flyTo([event.lat, event.lng], Math.max(map.getZoom(), 9), { duration: 1.2 });
  }
  return null;
}

/** Map confidence_level → marker fill-opacity (verified = solid, low = faded) */
function confidenceOpacity(level?: string | null): number {
  switch (level) {
    case "verified": return 0.95;
    case "high":     return 0.80;
    case "medium":   return 0.65;
    default:         return 0.45;
  }
}

export default function MapView() {
  const [search, setSearch]             = useState("");
  const [side, setSide]                 = useState<Side | "">("");
  const [category, setCategory]         = useState<string>("");
  const [onlyMapped, setOnlyMapped]     = useState(false);
  const [onlyImportant, setOnlyImportant] = useState(false);
  const [hidePropaganda, setHidePropaganda] = useState(false);
  const [drawerEvent, setDrawerEvent]   = useState<EventResponse | null>(null);
  const [latestLive, setLatestLive]     = useState<EventResponse | null>(null);

  const { data: eventsData, isLoading } = useListEvents({
    search: search || undefined,
    side: side || undefined,
    category: category || undefined,
    has_location: onlyMapped ? true : undefined,
    is_important: onlyImportant ? true : undefined,
    hide_propaganda: hidePropaganda ? true : undefined,
    limit: 300,
  });

  const { events: liveEvents, status: liveStatus } = useLiveEvents(100);

  const allEvents = useMemo(() => {
    const base = eventsData?.items ?? [];
    const ids  = new Set(base.map(e => e.id));
    const fresh = liveEvents.filter(e => {
      if (ids.has(e.id)) return false;
      if (side && e.side !== side) return false;
      if (category && e.category !== category) return false;
      if (onlyMapped && (!e.lat || !e.lng)) return false;
      if (onlyImportant && !e.is_important) return false;
      if (hidePropaganda && (e.propaganda_score ?? 0) >= 0.5) return false;
      return true;
    });
    return [...fresh, ...base];
  }, [eventsData, liveEvents, side, category, onlyMapped, onlyImportant, hidePropaganda]);

  useMemo(() => {
    const withLoc = liveEvents.find(e => e.lat && e.lng);
    if (withLoc) setLatestLive(withLoc);
  }, [liveEvents]);

  const mappedEvents = useMemo(() => allEvents.filter(e => e.lat && e.lng), [allEvents]);

  const markerColor = useCallback((event: EventResponse) => {
    return SIDE_HEX_COLORS[event.side ?? "neutral"] || SIDE_HEX_COLORS.neutral;
  }, []);

  const hasFilters = side || category || search || onlyMapped || onlyImportant || hidePropaganda;
  const clearFilters = () => {
    setSide(""); setCategory(""); setSearch("");
    setOnlyMapped(false); setOnlyImportant(false); setHidePropaganda(false);
  };

  return (
    <Layout>
      <div className="flex h-full w-full overflow-hidden">

        {/* ── Left Panel ──────────────────────────────────────────────── */}
        <div className="w-80 border-r border-border bg-card flex flex-col z-10 shadow-2xl">

          {/* Search + Filters */}
          <div className="p-3 border-b border-border space-y-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search events..."
                className="pl-8 bg-background border-border font-mono text-sm"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>

            {/* Side filter */}
            <div className="flex gap-1">
              <button
                onClick={() => setSide("")}
                className={`flex-1 py-1 rounded text-[9px] font-mono font-bold uppercase transition-colors ${
                  !side ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:text-foreground"
                }`}
              >ALL</button>
              {SIDES.map(s => (
                <button
                  key={s}
                  onClick={() => setSide(s === side ? "" : s)}
                  className={`flex-1 py-1 rounded text-[9px] font-mono font-bold uppercase transition-colors ${
                    side === s ? `${SIDE_COLORS[s]} text-white` : "bg-muted text-muted-foreground hover:text-foreground"
                  }`}
                >{s === "neutral" ? "NTR" : s.toUpperCase()}</button>
              ))}
            </div>

            {/* Category + geo + alerts + propaganda filter */}
            <div className="flex gap-1.5 flex-wrap">
              <Select value={category || "_all"} onValueChange={v => setCategory(v === "_all" ? "" : v)}>
                <SelectTrigger className="flex-1 min-w-[90px] font-mono text-[10px] bg-background border-border h-7">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_all" className="font-mono text-xs">All</SelectItem>
                  {CATEGORIES.map(c => (
                    <SelectItem key={c} value={c} className="font-mono text-xs capitalize">{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <button
                onClick={() => setOnlyMapped(v => !v)}
                title="Geolocated only"
                className={`px-2 rounded text-[9px] font-mono font-bold uppercase transition-colors border h-7 ${
                  onlyMapped
                    ? "bg-primary border-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:text-foreground"
                }`}
              >
                <MapPin className="w-3 h-3 inline" />
              </button>
              <button
                onClick={() => setOnlyImportant(v => !v)}
                title="Alerts only"
                className={`px-2 rounded text-[9px] font-mono font-bold uppercase transition-colors border h-7 ${
                  onlyImportant
                    ? "bg-orange-500/20 border-orange-500/50 text-orange-400"
                    : "border-border text-muted-foreground hover:text-orange-400"
                }`}
              >
                <Flame className="w-3 h-3 inline" />
              </button>
              <button
                onClick={() => setHidePropaganda(v => !v)}
                title="Hide high-propaganda content"
                className={`px-2 rounded text-[9px] font-mono font-bold uppercase transition-colors border h-7 ${
                  hidePropaganda
                    ? "bg-violet-500/20 border-violet-500/50 text-violet-400"
                    : "border-border text-muted-foreground hover:text-violet-400"
                }`}
              >
                <ShieldAlert className="w-3 h-3 inline" />
              </button>
              {hasFilters && (
                <button onClick={clearFilters} className="px-2 rounded text-[9px] font-mono text-muted-foreground hover:text-destructive transition-colors border border-border h-7">
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Stats row */}
            <div className="flex items-center justify-between text-[10px] font-mono text-muted-foreground">
              <span>{allEvents.length} events · {mappedEvents.length} on map</span>
              {liveStatus === "connected" ? (
                <span className="flex items-center gap-1 text-green-400">
                  <Radio className="w-3 h-3 animate-pulse" /> LIVE
                </span>
              ) : (
                <span className="text-amber-400">CONNECTING...</span>
              )}
            </div>
          </div>

          {/* Event List */}
          <ScrollArea className="flex-1 p-2">
            {isLoading ? (
              <div className="flex justify-center p-4">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            ) : (
              <div className="space-y-1.5">
                {allEvents.map((event) => (
                  <div
                    key={event.id}
                    className={`p-2.5 rounded border cursor-pointer transition-colors ${
                      drawerEvent?.id === event.id
                        ? "border-primary bg-primary/10"
                        : event.is_important
                        ? "border-orange-500/40 bg-orange-500/5 hover:border-orange-500/60"
                        : "border-border bg-background hover:border-primary/40"
                    }`}
                    style={{ borderLeft: `3px solid ${markerColor(event)}` }}
                    onClick={() => setDrawerEvent(event)}
                  >
                    <div className="flex items-center gap-1.5 mb-1.5 flex-wrap">
                      {event.is_important && (
                        <Flame className="w-3 h-3 text-orange-500 shrink-0" />
                      )}
                      <Badge
                        className={`text-[8px] font-mono px-1 py-0 border-none text-white ${SIDE_COLORS[event.side ?? "neutral"] || SIDE_COLORS.neutral}`}
                      >
                        {SIDE_LABELS_EN[event.side ?? "neutral"]}
                      </Badge>
                      <Badge
                        className={`text-[8px] font-mono px-1 py-0 border-none text-white ${CATEGORY_COLORS[event.category] || CATEGORY_COLORS.other}`}
                      >
                        {event.category}
                      </Badge>
                      {event.confidence_level && event.confidence_level !== "low" && (
                        <Badge
                          className={`text-[8px] font-mono px-1 py-0 border-none text-white ${CONFIDENCE_LEVEL_COLORS[event.confidence_level] ?? "bg-slate-500"}`}
                        >
                          {CONFIDENCE_LEVEL_LABELS[event.confidence_level]}
                        </Badge>
                      )}
                      <span className="text-[9px] text-muted-foreground ml-auto whitespace-nowrap">
                        {new Date(event.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    <h3 className="text-xs font-medium leading-tight line-clamp-2" dir="rtl">
                      {event.title_he || event.title}
                    </h3>
                    {event.location_name && (
                      <p className="text-[10px] text-muted-foreground mt-1 truncate">
                        📍 {event.location_name}
                      </p>
                    )}
                  </div>
                ))}
                {allEvents.length === 0 && (
                  <p className="text-center text-xs text-muted-foreground py-8 font-mono">No events</p>
                )}
              </div>
            )}
          </ScrollArea>
        </div>

        {/* ── Map ─────────────────────────────────────────────────────── */}
        <div className="flex-1 relative bg-black">
          <MapContainer
            center={[32.5, 35.2]}
            zoom={8}
            className="w-full h-full"
            zoomControl={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />

            <LiveEventFlyTo event={latestLive} />

            {mappedEvents.map((event) => {
              const color = markerColor(event);
              const isSelected = drawerEvent?.id === event.id;
              const isLive = liveEvents.some(e => e.id === event.id);
              const isImportant = !!event.is_important;
              const opacity = isSelected || isImportant
                ? 0.95
                : confidenceOpacity(event.confidence_level);

              return (
                <CircleMarker
                  key={event.id}
                  center={[event.lat!, event.lng!]}
                  radius={isSelected ? 12 : isImportant ? 10 : isLive ? 8 : 6}
                  pathOptions={{
                    fillColor: color,
                    fillOpacity: opacity,
                    color: isSelected ? "#ffffff" : isImportant ? "#f97316" : color,
                    weight: isSelected ? 3 : isImportant ? 2.5 : isLive ? 2 : 1,
                  }}
                  eventHandlers={{ click: () => setDrawerEvent(event) }}
                >
                  <Popup className="custom-popup">
                    <div className="p-1 min-w-[220px]">
                      <div className="flex gap-1 mb-2 flex-wrap">
                        <Badge className={`text-[9px] font-mono border-none text-white ${SIDE_COLORS[event.side ?? "neutral"]}`}>
                          {SIDE_LABELS_EN[event.side ?? "neutral"]}
                        </Badge>
                        <Badge className={`text-[9px] font-mono border-none text-white ${CATEGORY_COLORS[event.category]}`}>
                          {event.category}
                        </Badge>
                        {event.confidence_level && event.confidence_level !== "low" && (
                          <Badge className={`text-[9px] font-mono border-none text-white ${CONFIDENCE_LEVEL_COLORS[event.confidence_level] ?? "bg-slate-500"}`}>
                            {CONFIDENCE_LEVEL_LABELS[event.confidence_level]}
                          </Badge>
                        )}
                        {isImportant && (
                          <Badge className="text-[9px] font-mono border-none bg-orange-500 text-white">⚠ ALERT</Badge>
                        )}
                        {isLive && (
                          <Badge className="text-[9px] font-mono border-none bg-green-600 text-white">LIVE</Badge>
                        )}
                      </div>
                      <h4 className="font-bold text-sm mb-2 leading-tight" dir="rtl">
                        {event.title_he || event.title}
                      </h4>
                      <div className="text-[10px] text-muted-foreground space-y-0.5" dir="ltr">
                        {event.location_name && <div>📍 {event.location_name}</div>}
                        {event.source_name && <div>📡 {event.source_name}</div>}
                        <div>Confidence: {(event.confidence * 100).toFixed(0)}%</div>
                        {(event.confirmation_count ?? 0) > 0 && (
                          <div>✓ Confirmed by {event.confirmation_count} source{event.confirmation_count !== 1 ? "s" : ""}</div>
                        )}
                        <div>{new Date(event.created_at).toLocaleString()}</div>
                      </div>
                      <button
                        className="mt-2 w-full text-[9px] font-mono text-primary hover:underline text-left"
                        onClick={() => setDrawerEvent(event)}
                      >
                        VIEW DETAILS →
                      </button>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>

          {/* Legend overlay */}
          <div className="absolute bottom-6 left-4 z-[1000] bg-background/90 backdrop-blur border border-border rounded-md p-3 space-y-1.5">
            <p className="text-[9px] font-mono font-bold uppercase text-muted-foreground tracking-widest mb-2">Legend</p>
            {SIDES.map(s => (
              <div key={s} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: SIDE_HEX_COLORS[s] }} />
                <span className={`text-[10px] font-mono ${SIDE_TEXT_COLORS[s]}`}>{SIDE_LABELS_EN[s]}</span>
              </div>
            ))}
            <div className="flex items-center gap-2 border-t border-border pt-1.5 mt-1.5">
              <div className="w-3 h-3 rounded-full border-2 border-orange-500" style={{ background: "transparent" }} />
              <span className="text-[10px] font-mono text-orange-400">Alert</span>
            </div>
            <div className="border-t border-border pt-1.5 mt-0.5">
              <p className="text-[9px] font-mono text-muted-foreground mb-1">Opacity = Intel Level</p>
              <div className="flex gap-1">
                {(["low","medium","high","verified"] as const).map(l => (
                  <div
                    key={l}
                    className="w-4 h-4 rounded-sm"
                    title={CONFIDENCE_LEVEL_LABELS[l]}
                    style={{ background: "#3b82f6", opacity: confidenceOpacity(l) }}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>

      </div>

      {/* Event detail drawer */}
      <EventDrawer event={drawerEvent} onClose={() => setDrawerEvent(null)} />
    </Layout>
  );
}
