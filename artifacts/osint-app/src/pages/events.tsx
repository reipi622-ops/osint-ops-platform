import { Layout } from "@/components/layout";
import { EventDrawer } from "@/components/event-drawer";
import { EscalationBadge } from "@/components/escalation-badge";
import { useListEvents, useListSources } from "@workspace/api-client-react";
import { useState, useMemo, useCallback } from "react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  CATEGORY_COLORS, SIDE_COLORS, SIDE_LABELS_EN, SIDE_HEX_COLORS, CATEGORIES,
  CONFIDENCE_LEVEL_COLORS, CONFIDENCE_LEVEL_LABELS,
} from "@/lib/constants";
import { Loader2, Search, X, Radio, Flame, ShieldAlert, Star, Download, Bookmark } from "lucide-react";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { useLiveEvents } from "@/hooks/use-live-events";
import type { EventResponse } from "@workspace/api-client-react";

const SIDES = ["red", "blue", "neutral"] as const;
type Side = typeof SIDES[number];
const CONF_LEVELS = ["low", "medium", "high", "verified"] as const;
type ConfLevel = typeof CONF_LEVELS[number];

const BOOKMARK_KEY = "osint_bookmarks";

function getStoredBookmarks(): Set<number> {
  try {
    const raw = localStorage.getItem(BOOKMARK_KEY);
    return new Set(raw ? (JSON.parse(raw) as number[]) : []);
  } catch { return new Set(); }
}

function saveBookmarks(set: Set<number>): void {
  localStorage.setItem(BOOKMARK_KEY, JSON.stringify([...set]));
}

export default function EventsList() {
  const [search, setSearch]               = useState("");
  const [side, setSide]                   = useState<Side | "">("");
  const [category, setCategory]           = useState<string>("");
  const [sourceName, setSourceName]       = useState<string>("");
  const [onlyImportant, setOnlyImportant] = useState(false);
  const [confLevel, setConfLevel]         = useState<ConfLevel | "">("");
  const [hidePropaganda, setHidePropaganda] = useState(false);
  const [showBookmarked, setShowBookmarked] = useState(false);
  const [page, setPage]                   = useState(0);
  const [drawerEvent, setDrawerEvent]     = useState<EventResponse | null>(null);
  const [bookmarks, setBookmarks]         = useState<Set<number>>(getStoredBookmarks);
  const PAGE = 100;

  const { data: eventsData, isLoading } = useListEvents({
    search: search || undefined,
    side: side || undefined,
    category: category || undefined,
    source_name: sourceName || undefined,
    is_important: onlyImportant ? true : undefined,
    confidence_level: confLevel || undefined,
    hide_propaganda: hidePropaganda ? true : undefined,
    limit: PAGE,
    offset: page * PAGE,
  });

  const { data: sourcesData } = useListSources();
  const { events: liveEvents, status: liveStatus } = useLiveEvents(50);

  const allEvents = useMemo(() => {
    const base = eventsData?.items ?? [];
    if (!liveEvents.length) return base;
    const ids = new Set(base.map(e => e.id));
    const fresh = liveEvents.filter(e => {
      if (ids.has(e.id)) return false;
      if (side && e.side !== side) return false;
      if (category && e.category !== category) return false;
      if (sourceName && !e.source_name?.toLowerCase().includes(sourceName.toLowerCase())) return false;
      if (onlyImportant && !e.is_important) return false;
      if (confLevel && e.confidence_level !== confLevel) return false;
      if (hidePropaganda && (e.propaganda_score ?? 0) >= 0.5) return false;
      if (search) {
        const q = search.toLowerCase();
        if (!e.title?.toLowerCase().includes(q) &&
            !e.title_he?.toLowerCase().includes(q) &&
            !e.location_name?.toLowerCase().includes(q)) return false;
      }
      return true;
    });
    return [...fresh, ...base];
  }, [eventsData, liveEvents, side, category, sourceName, search, onlyImportant, confLevel, hidePropaganda]);

  const displayedEvents = useMemo(
    () => showBookmarked ? allEvents.filter(e => bookmarks.has(e.id)) : allEvents,
    [allEvents, showBookmarked, bookmarks],
  );

  const hasFilters = side || category || sourceName || search || onlyImportant || confLevel || hidePropaganda;

  const clearFilters = () => {
    setSide(""); setCategory(""); setSourceName(""); setSearch("");
    setOnlyImportant(false); setConfLevel(""); setHidePropaganda(false); setPage(0);
  };

  const uniqueSources = useMemo(() => {
    const names = new Set<string>();
    (sourcesData ?? []).forEach(s => s.name && names.add(s.name));
    (eventsData?.items ?? []).forEach(e => e.source_name && names.add(e.source_name));
    return [...names].sort();
  }, [sourcesData, eventsData]);

  const handleBookmark = useCallback((e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    setBookmarks(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      saveBookmarks(next);
      return next;
    });
  }, []);

  const handleExport = useCallback(async (format: "csv" | "json") => {
    const params = new URLSearchParams({ format, limit: "5000" });
    if (side)           params.set("side", side);
    if (category)       params.set("category", category);
    if (onlyImportant)  params.set("is_important", "true");
    if (search)         params.set("search", search);
    if (sourceName)     params.set("source_name", sourceName);
    if (confLevel)      params.set("confidence_level", confLevel);
    if (hidePropaganda) params.set("hide_propaganda", "true");
    try {
      const res = await fetch(`/api/events/export?${params}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `osint_events_${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch { /* silent — browser will handle download errors */ }
  }, [side, category, onlyImportant, search, sourceName, confLevel, hidePropaganda]);

  return (
    <Layout>
      <div className="p-6 h-full flex flex-col gap-4">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold font-mono tracking-tight uppercase">Event Log</h2>
            {eventsData && (
              <span className="text-xs font-mono text-muted-foreground">
                {eventsData.total.toLocaleString()} events
              </span>
            )}
            {liveStatus === "connected" && (
              <span className="flex items-center gap-1 text-[10px] font-mono text-green-400">
                <Radio className="w-3 h-3 animate-pulse" />
                LIVE
              </span>
            )}
          </div>
          {/* Export */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="font-mono text-xs h-8 gap-1.5">
                <Download className="w-3.5 h-3.5" />
                EXPORT
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem className="font-mono text-xs cursor-pointer" onClick={() => handleExport("csv")}>
                Download CSV
              </DropdownMenuItem>
              <DropdownMenuItem className="font-mono text-xs cursor-pointer" onClick={() => handleExport("json")}>
                Download JSON
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* ── Filter Bar ──────────────────────────────────────────────── */}
        <div className="flex flex-wrap gap-2 items-center">
          {/* Search */}
          <div className="relative flex-1 min-w-[180px] max-w-xs">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search events..."
              className="pl-8 bg-card border-border font-mono text-sm"
              value={search}
              onChange={e => { setSearch(e.target.value); setPage(0); }}
            />
          </div>

          {/* Side filter */}
          <div className="flex items-center gap-1 bg-card border border-border rounded-md p-1">
            <button
              onClick={() => { setSide(""); setPage(0); }}
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-colors ${
                !side ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >ALL</button>
            {SIDES.map(s => (
              <button
                key={s}
                onClick={() => { setSide(s === side ? "" : s); setPage(0); }}
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-colors ${
                  side === s
                    ? `${SIDE_COLORS[s]} text-white`
                    : "text-muted-foreground hover:text-foreground"
                }`}
                style={{ borderLeft: `2px solid ${SIDE_HEX_COLORS[s]}22` }}
              >{SIDE_LABELS_EN[s]}</button>
            ))}
          </div>

          {/* Category filter */}
          <Select value={category || "_all"} onValueChange={v => { setCategory(v === "_all" ? "" : v); setPage(0); }}>
            <SelectTrigger className="w-[150px] font-mono text-xs bg-card border-border h-9">
              <SelectValue placeholder="Category" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_all" className="font-mono text-xs">All Categories</SelectItem>
              {CATEGORIES.map(c => (
                <SelectItem key={c} value={c} className="font-mono text-xs capitalize">{c}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Source filter */}
          <Select value={sourceName || "_all"} onValueChange={v => { setSourceName(v === "_all" ? "" : v); setPage(0); }}>
            <SelectTrigger className="w-[180px] font-mono text-xs bg-card border-border h-9">
              <SelectValue placeholder="Source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_all" className="font-mono text-xs">All Sources</SelectItem>
              {uniqueSources.map(s => (
                <SelectItem key={s} value={s} className="font-mono text-xs">{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Confidence level filter */}
          <Select value={confLevel || "_all"} onValueChange={v => { setConfLevel(v === "_all" ? "" : v as ConfLevel); setPage(0); }}>
            <SelectTrigger className="w-[140px] font-mono text-xs bg-card border-border h-9">
              <SelectValue placeholder="Intel Level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="_all" className="font-mono text-xs">All Levels</SelectItem>
              {CONF_LEVELS.map(l => (
                <SelectItem key={l} value={l} className="font-mono text-xs">
                  <span className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full inline-block ${CONFIDENCE_LEVEL_COLORS[l]}`} />
                    {CONFIDENCE_LEVEL_LABELS[l]}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Alerts-only toggle */}
          <button
            onClick={() => { setOnlyImportant(v => !v); setPage(0); }}
            className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-[10px] font-mono font-bold uppercase border transition-colors ${
              onlyImportant
                ? "bg-orange-500/20 border-orange-500/50 text-orange-400"
                : "border-border text-muted-foreground hover:text-orange-400 hover:border-orange-500/40"
            }`}
          >
            <Flame className="w-3 h-3" />
            ALERTS
          </button>

          {/* Hide propaganda toggle */}
          <button
            onClick={() => { setHidePropaganda(v => !v); setPage(0); }}
            title="Hide high-propaganda content"
            className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-[10px] font-mono font-bold uppercase border transition-colors ${
              hidePropaganda
                ? "bg-violet-500/20 border-violet-500/50 text-violet-400"
                : "border-border text-muted-foreground hover:text-violet-400 hover:border-violet-500/40"
            }`}
          >
            <ShieldAlert className="w-3 h-3" />
            FILTER BIAS
          </button>

          {/* Bookmarked toggle */}
          <button
            onClick={() => setShowBookmarked(v => !v)}
            title="Show only bookmarked events"
            className={`flex items-center gap-1 px-3 py-1.5 rounded-md text-[10px] font-mono font-bold uppercase border transition-colors ${
              showBookmarked
                ? "bg-yellow-500/20 border-yellow-500/50 text-yellow-400"
                : "border-border text-muted-foreground hover:text-yellow-400 hover:border-yellow-500/40"
            }`}
          >
            <Bookmark className="w-3 h-3" />
            BOOKMARKED {bookmarks.size > 0 && `(${bookmarks.size})`}
          </button>

          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={clearFilters} className="font-mono text-xs text-muted-foreground h-9">
              <X className="w-3.5 h-3.5 mr-1" /> Clear
            </Button>
          )}
        </div>

        {/* ── Table ───────────────────────────────────────────────────── */}
        <div className="flex-1 bg-card rounded-md border border-border overflow-hidden flex flex-col min-h-0">
          {isLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : (
            <div className="overflow-auto flex-1">
              <Table>
                <TableHeader className="bg-muted/50 sticky top-0 z-10 backdrop-blur-sm">
                  <TableRow>
                    <TableHead className="w-[28px] font-mono text-xs"></TableHead>
                    <TableHead className="w-[32px] font-mono text-xs"></TableHead>
                    <TableHead className="w-[110px] font-mono text-xs">TIME</TableHead>
                    <TableHead className="font-mono text-xs w-[80px]">SIDE</TableHead>
                    <TableHead className="font-mono text-xs w-[120px]">CATEGORY</TableHead>
                    <TableHead className="font-mono text-xs">TITLE (HE)</TableHead>
                    <TableHead className="font-mono text-xs w-[130px]">LOCATION</TableHead>
                    <TableHead className="font-mono text-xs w-[100px]">INTEL LEVEL</TableHead>
                    <TableHead className="font-mono text-xs w-[110px]">ESCALATION</TableHead>
                    <TableHead className="font-mono text-xs w-[120px]">CONFIDENCE</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {displayedEvents.map((event: EventResponse) => (
                    <TableRow
                      key={event.id}
                      className="hover:bg-muted/40 cursor-pointer transition-colors border-border"
                      style={{ borderLeft: `2px solid ${SIDE_HEX_COLORS[event.side ?? "neutral"]}` }}
                      onClick={() => setDrawerEvent(event)}
                    >
                      {/* Alert flame indicator */}
                      <TableCell className="pr-0 text-center">
                        {event.is_important && (
                          <Flame className="w-3.5 h-3.5 text-orange-500 mx-auto" />
                        )}
                      </TableCell>
                      {/* Bookmark star */}
                      <TableCell className="px-1 text-center">
                        <button
                          onClick={e => handleBookmark(e, event.id)}
                          className={`transition-colors ${bookmarks.has(event.id) ? "text-yellow-400" : "text-muted-foreground/30 hover:text-yellow-400"}`}
                          title={bookmarks.has(event.id) ? "Remove bookmark" : "Bookmark"}
                        >
                          <Star className={`w-3 h-3 ${bookmarks.has(event.id) ? "fill-yellow-400" : ""}`} />
                        </button>
                      </TableCell>
                      <TableCell className="font-mono text-[10px] text-muted-foreground whitespace-nowrap">
                        {new Date(event.created_at).toLocaleString(undefined, {
                          month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                        })}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`font-mono text-[9px] uppercase border-none text-white ${SIDE_COLORS[event.side ?? "neutral"] || SIDE_COLORS.neutral}`}
                        >
                          {SIDE_LABELS_EN[event.side ?? "neutral"] ?? "Neutral"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`font-mono text-[9px] uppercase border-none text-white ${CATEGORY_COLORS[event.category] || CATEGORY_COLORS.other}`}
                        >
                          {event.category}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-medium max-w-[320px]" dir="rtl">
                        <div className="truncate text-sm">{event.title_he || event.title}</div>
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap truncate max-w-[130px]">
                        {event.location_name || "—"}
                      </TableCell>
                      <TableCell>
                        {event.confidence_level && (
                          <Badge
                            className={`font-mono text-[9px] uppercase border-none text-white ${
                              CONFIDENCE_LEVEL_COLORS[event.confidence_level] ?? "bg-slate-500"
                            }`}
                          >
                            {CONFIDENCE_LEVEL_LABELS[event.confidence_level] ?? event.confidence_level}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <EscalationBadge level={event.escalation_level} className="text-[9px]" />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Progress value={event.confidence * 100} className="h-1.5 w-14" />
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {(event.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {displayedEvents.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={10} className="text-center py-10 text-muted-foreground font-mono text-sm">
                        {showBookmarked ? "No bookmarked events" : "No events match the current filters"}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        {/* ── Pagination ──────────────────────────────────────────────── */}
        {eventsData && eventsData.total > PAGE && !showBookmarked && (
          <div className="flex items-center justify-between text-xs font-mono text-muted-foreground">
            <span>
              Showing {page * PAGE + 1}–{Math.min((page + 1) * PAGE, eventsData.total)} of {eventsData.total}
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" className="h-7 text-xs font-mono"
                disabled={page === 0} onClick={() => setPage(p => p - 1)}>
                ← Prev
              </Button>
              <Button size="sm" variant="outline" className="h-7 text-xs font-mono"
                disabled={(page + 1) * PAGE >= eventsData.total} onClick={() => setPage(p => p + 1)}>
                Next →
              </Button>
            </div>
          </div>
        )}

      </div>

      {/* Event detail drawer */}
      <EventDrawer event={drawerEvent} onClose={() => setDrawerEvent(null)} />
    </Layout>
  );
}
