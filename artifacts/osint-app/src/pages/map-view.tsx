import { Layout } from "@/components/layout";
import { useListEvents, useGetEvent, getGetEventQueryKey } from "@workspace/api-client-react";
import { useState, useMemo, useCallback } from "react";
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from "react-leaflet";
import {
  SIDE_HEX_COLORS, SIDE_COLORS, SIDE_LABELS, SIDE_TEXT_COLORS,
  CATEGORY_COLORS, CATEGORY_HEX_COLORS, CATEGORIES,
} from "@/lib/constants";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Search, Loader2, Radio, X, MapPin } from "lucide-react";
import { useLiveEvents } from "@/hooks/use-live-events";
import type { EventResponse } from "@workspace/api-client-react";

const SIDES = ["red", "blue", "neutral"] as const;
type Side = typeof SIDES[number];

// Fly to newly added live event marker
function LiveEventFlyTo({ event }: { event: EventResponse | null }) {
  const map = useMap();
  if (event?.lat && event?.lng) {
    map.flyTo([event.lat, event.lng], Math.max(map.getZoom(), 9), { duration: 1.2 });
  }
  return null;
}

export default function MapView() {
  const [search, setSearch]         = useState("");
  const [side, setSide]             = useState<Side | "">("");
  const [category, setCategory]     = useState<string>("");
  const [onlyMapped, setOnlyMapped] = useState(false);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [latestLive, setLatestLive]  = useState<EventResponse | null>(null);

  const { data: eventsData, isLoading } = useListEvents({
    search: search || undefined,
    side: side || undefined,
    category: category || undefined,
    has_location: onlyMapped ? true : undefined,
    limit: 200,
  });

  const { data: selectedEvent } = useGetEvent(selectedEventId!, {
    query: { queryKey: getGetEventQueryKey(selectedEventId!), enabled: !!selectedEventId },
  });

  const { events: liveEvents, status: liveStatus } = useLiveEvents(100);

  // Merge live events with DB results; apply active filters locally
  const allEvents = useMemo(() => {
    const base = eventsData?.items ?? [];
    const ids  = new Set(base.map(e => e.id));
    const fresh = liveEvents.filter(e => {
      if (ids.has(e.id)) return false;
      if (side && e.side !== side) return false;
      if (category && e.category !== category) return false;
      if (onlyMapped && (!e.lat || !e.lng)) return false;
      return true;
    });
    return [...fresh, ...base];
  }, [eventsData, liveEvents, side, category, onlyMapped]);

  // Track the very latest live event that has a location for flyTo
  useMemo(() => {
    const withLoc = liveEvents.find(e => e.lat && e.lng);
    if (withLoc) setLatestLive(withLoc);
  }, [liveEvents]);

  const mappedEvents = useMemo(() => allEvents.filter(e => e.lat && e.lng), [allEvents]);

  const markerColor = useCallback((event: EventResponse) => {
    return SIDE_HEX_COLORS[event.side ?? "neutral"] || SIDE_HEX_COLORS.neutral;
  }, []);

  const hasFilters = side || category || search || onlyMapped;
  const clearFilters = () => { setSide(""); setCategory(""); setSearch(""); setOnlyMapped(false); };

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

            {/* Category + mapped-only */}
            <div className="flex gap-2">
              <Select value={category || "_all"} onValueChange={v => setCategory(v === "_all" ? "" : v)}>
                <SelectTrigger className="flex-1 font-mono text-[10px] bg-background border-border h-7">
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
                className={`px-2 rounded text-[9px] font-mono font-bold uppercase transition-colors border ${
                  onlyMapped
                    ? "bg-primary border-primary text-primary-foreground"
                    : "border-border text-muted-foreground hover:text-foreground"
                }`}
              >
                <MapPin className="w-3 h-3 inline mr-0.5" />GEO
              </button>
              {hasFilters && (
                <button onClick={clearFilters} className="px-2 rounded text-[9px] font-mono text-muted-foreground hover:text-destructive transition-colors border border-border">
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
                      selectedEventId === event.id
                        ? "border-primary bg-primary/10"
                        : "border-border bg-background hover:border-primary/40"
                    }`}
                    style={{ borderLeft: `3px solid ${markerColor(event)}` }}
                    onClick={() => setSelectedEventId(event.id)}
                  >
                    <div className="flex items-center gap-1.5 mb-1.5">
                      <Badge
                        className={`text-[8px] font-mono px-1 py-0 border-none text-white ${SIDE_COLORS[event.side ?? "neutral"] || SIDE_COLORS.neutral}`}
                      >
                        {SIDE_LABELS[event.side ?? "neutral"]}
                      </Badge>
                      <Badge
                        className={`text-[8px] font-mono px-1 py-0 border-none text-white ${CATEGORY_COLORS[event.category] || CATEGORY_COLORS.other}`}
                      >
                        {event.category}
                      </Badge>
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
            center={[31.5, 35.0]}
            zoom={7}
            className="w-full h-full"
            zoomControl={false}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />

            {/* Fly to new live events */}
            <LiveEventFlyTo event={latestLive} />

            {mappedEvents.map((event) => {
              const color = markerColor(event);
              const isSelected = selectedEventId === event.id;
              const isLive = liveEvents.some(e => e.id === event.id);
              return (
                <CircleMarker
                  key={event.id}
                  center={[event.lat!, event.lng!]}
                  radius={isSelected ? 10 : isLive ? 8 : 6}
                  pathOptions={{
                    fillColor: color,
                    fillOpacity: isSelected ? 0.95 : 0.75,
                    color: isSelected ? "#ffffff" : color,
                    weight: isSelected ? 2.5 : isLive ? 2 : 1,
                  }}
                  eventHandlers={{ click: () => setSelectedEventId(event.id) }}
                >
                  <Popup className="custom-popup">
                    <div className="p-1 min-w-[220px]">
                      <div className="flex gap-1 mb-2">
                        <Badge className={`text-[9px] font-mono border-none text-white ${SIDE_COLORS[event.side ?? "neutral"]}`}>
                          {SIDE_LABELS[event.side ?? "neutral"]}
                        </Badge>
                        <Badge className={`text-[9px] font-mono border-none text-white ${CATEGORY_COLORS[event.category]}`}>
                          {event.category}
                        </Badge>
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
                        <div>{new Date(event.created_at).toLocaleString()}</div>
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>

          {/* Legend overlay */}
          <div className="absolute bottom-6 left-4 z-[1000] bg-background/90 backdrop-blur border border-border rounded-md p-3 space-y-1.5">
            <p className="text-[9px] font-mono font-bold uppercase text-muted-foreground tracking-widest mb-2">Side Legend</p>
            {SIDES.map(s => (
              <div key={s} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full" style={{ background: SIDE_HEX_COLORS[s] }} />
                <span className={`text-[10px] font-mono ${SIDE_TEXT_COLORS[s]}`}>{SIDE_LABELS[s]}</span>
              </div>
            ))}
          </div>

          {/* Selected event detail overlay */}
          {selectedEvent && (
            <div className="absolute top-4 right-4 z-[1000] bg-background/95 backdrop-blur border border-border rounded-md p-4 w-72 shadow-xl">
              <div className="flex items-start justify-between mb-3">
                <div className="flex gap-1 flex-wrap">
                  <Badge className={`text-[9px] font-mono border-none text-white ${SIDE_COLORS[selectedEvent.side ?? "neutral"]}`}>
                    {SIDE_LABELS[selectedEvent.side ?? "neutral"]}
                  </Badge>
                  <Badge className={`text-[9px] font-mono border-none text-white ${CATEGORY_COLORS[selectedEvent.category]}`}>
                    {selectedEvent.category}
                  </Badge>
                </div>
                <button onClick={() => setSelectedEventId(null)} className="text-muted-foreground hover:text-foreground ml-2 shrink-0">
                  <X className="w-4 h-4" />
                </button>
              </div>
              <h4 className="font-bold text-sm leading-snug mb-3" dir="rtl">
                {selectedEvent.title_he || selectedEvent.title}
              </h4>
              {selectedEvent.description_he && (
                <p className="text-xs text-muted-foreground leading-relaxed mb-3 line-clamp-4" dir="rtl">
                  {selectedEvent.description_he}
                </p>
              )}
              <div className="text-[10px] font-mono text-muted-foreground space-y-1 border-t border-border pt-2">
                {selectedEvent.location_name && <div>📍 {selectedEvent.location_name}</div>}
                {selectedEvent.source_name && <div>📡 {selectedEvent.source_name}</div>}
                <div>Confidence: {(selectedEvent.confidence * 100).toFixed(0)}%</div>
                <div>{new Date(selectedEvent.created_at).toLocaleString()}</div>
              </div>
            </div>
          )}
        </div>

      </div>
    </Layout>
  );
}
