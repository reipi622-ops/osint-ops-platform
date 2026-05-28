import { Layout } from "@/components/layout";
import { EventDrawer } from "@/components/event-drawer";
import { useListAlerts, getListAlertsQueryKey } from "@workspace/api-client-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Loader2, Bell, Flame, MapPin, Radio } from "lucide-react";
import {
  SIDE_COLORS, SIDE_LABELS_EN, SIDE_HEX_COLORS, CATEGORY_COLORS,
  IMPORTANCE_TAG_LABELS,
} from "@/lib/constants";
import type { EventResponse } from "@workspace/api-client-react";

const SIDES = ["red", "blue", "neutral"] as const;
type Side = typeof SIDES[number];

function timeAgo(date: string): string {
  const secs = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (secs < 60)  return `${secs}s ago`;
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`;
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`;
  return `${Math.floor(secs / 86400)}d ago`;
}

export default function AlertsPage() {
  const [sideFilter, setSideFilter] = useState<Side | "">("");
  const [drawerEvent, setDrawerEvent] = useState<EventResponse | null>(null);

  const alertParams = { side: sideFilter || undefined, limit: 100 };
  const { data, isLoading, dataUpdatedAt } = useListAlerts(
    alertParams,
    { query: { queryKey: getListAlertsQueryKey(alertParams), refetchInterval: 10_000 } },
  );

  const alerts = data?.items ?? [];

  return (
    <Layout>
      <div className="p-6 h-full flex flex-col gap-4 overflow-hidden">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-orange-500" />
            <h2 className="text-2xl font-bold font-mono tracking-tight uppercase">
              Alert Feed
            </h2>
            {data && (
              <span className="text-xs font-mono text-muted-foreground">
                {data.total} alerts
              </span>
            )}
            {/* Live refresh indicator */}
            <span className="flex items-center gap-1 text-[10px] font-mono text-orange-400">
              <Radio className="w-3 h-3 animate-pulse" />
              LIVE · {dataUpdatedAt
                ? new Date(dataUpdatedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
                : "—"}
            </span>
          </div>

          {/* Side filter pills */}
          <div className="flex items-center gap-1 bg-card border border-border rounded-md p-1">
            <button
              onClick={() => setSideFilter("")}
              className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-colors ${
                !sideFilter ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
              }`}
            >ALL</button>
            {SIDES.map(s => (
              <button
                key={s}
                onClick={() => setSideFilter(s === sideFilter ? "" : s)}
                className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-colors ${
                  sideFilter === s ? `${SIDE_COLORS[s]} text-white` : "text-muted-foreground hover:text-foreground"
                }`}
              >{SIDE_LABELS_EN[s]}</button>
            ))}
          </div>
        </div>

        {/* ── Alert Cards ─────────────────────────────────────────────── */}
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <Bell className="w-12 h-12 opacity-20" />
            <p className="font-mono text-sm">No alerts yet — monitoring channels...</p>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 pb-4">
              {alerts.map((event: EventResponse) => {
                const tags = event.importance_tags
                  ? event.importance_tags.split(",").filter(Boolean)
                  : [];
                return (
                  <div
                    key={event.id}
                    onClick={() => setDrawerEvent(event)}
                    className="cursor-pointer rounded-md border bg-card p-4 hover:bg-muted/40 transition-colors relative overflow-hidden"
                    style={{ borderLeft: `3px solid ${SIDE_HEX_COLORS[event.side ?? "neutral"]}` }}
                  >
                    {/* Subtle threat glow for high-score alerts */}
                    {(event.importance_score ?? 0) >= 0.8 && (
                      <div className="absolute inset-0 bg-red-950/20 pointer-events-none rounded-md" />
                    )}

                    {/* Top row: badges + time */}
                    <div className="flex items-center gap-1.5 mb-2 relative">
                      <Badge
                        className={`text-[9px] font-mono border-none text-white shrink-0 ${SIDE_COLORS[event.side ?? "neutral"]}`}
                      >
                        {SIDE_LABELS_EN[event.side ?? "neutral"]}
                      </Badge>
                      <Badge
                        className={`text-[9px] font-mono border-none text-white shrink-0 uppercase ${CATEGORY_COLORS[event.category] || CATEGORY_COLORS.other}`}
                      >
                        {event.category}
                      </Badge>
                      {(event.importance_score ?? 0) >= 0.8 && (
                        <Badge className="text-[9px] font-mono border-none bg-red-600 text-white shrink-0 animate-pulse">
                          HIGH
                        </Badge>
                      )}
                      <span className="ml-auto text-[10px] font-mono text-muted-foreground shrink-0">
                        {timeAgo(event.created_at)}
                      </span>
                    </div>

                    {/* Title */}
                    <h3
                      className="text-sm font-bold leading-snug mb-2 line-clamp-2 relative"
                      dir="rtl"
                    >
                      {event.title_he || event.title}
                    </h3>

                    {/* Importance tags */}
                    {tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2 relative">
                        {tags.map((tag) => {
                          const meta = IMPORTANCE_TAG_LABELS[tag];
                          return (
                            <span
                              key={tag}
                              className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[9px] font-mono bg-orange-500/15 text-orange-400 border border-orange-500/25"
                            >
                              {meta?.icon ?? "▲"} {meta?.label ?? tag}
                            </span>
                          );
                        })}
                      </div>
                    )}

                    {/* Footer: location + source + score */}
                    <div className="flex items-center gap-3 text-[10px] font-mono text-muted-foreground relative">
                      {event.location_name && (
                        <span className="flex items-center gap-0.5 truncate">
                          <MapPin className="w-2.5 h-2.5 shrink-0" />
                          {event.location_name}
                        </span>
                      )}
                      <span className="truncate max-w-[140px]">{event.source_name || "—"}</span>
                      <span className="ml-auto flex items-center gap-1 shrink-0">
                        <Flame className="w-3 h-3 text-orange-500" />
                        {((event.importance_score ?? 0) * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <EventDrawer event={drawerEvent} onClose={() => setDrawerEvent(null)} />
    </Layout>
  );
}
