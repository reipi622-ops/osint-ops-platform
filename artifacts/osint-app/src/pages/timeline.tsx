import { Layout } from "@/components/layout";
import { useGetEventsTimeline, getGetEventsTimelineQueryKey } from "@workspace/api-client-react";
import { useState, useRef, useEffect, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts";
import { Loader2, Clock, Play, Pause, SkipBack } from "lucide-react";
import { SIDE_CHART_COLORS, SIDE_LABELS_EN } from "@/lib/constants";

const WINDOWS = [
  { label: "6H",   value: 6   },
  { label: "12H",  value: 12  },
  { label: "24H",  value: 24  },
  { label: "48H",  value: 48  },
  { label: "7D",   value: 168 },
] as const;

type WindowHours = typeof WINDOWS[number]["value"];

const SCRUB_WINDOW = 2;
const SPEEDS = [
  { label: "1×", ms: 2000 },
  { label: "4×", ms: 500  },
] as const;
type SpeedIdx = 0 | 1;

function formatHour(isoHour: string, windowHours: WindowHours): string {
  const d = new Date(isoHour);
  if (windowHours <= 24) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric", hour: "2-digit" });
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ name: string; value: number; fill: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload?.length || !label) return null;
  const total = payload.reduce((s, p) => s + (p.value ?? 0), 0);
  return (
    <div className="bg-background border border-border rounded-md p-3 text-xs font-mono shadow-xl">
      <p className="text-muted-foreground mb-2">{new Date(label).toLocaleString([], {
        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
      })}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full shrink-0" style={{ background: p.fill }} />
          <span className="text-muted-foreground capitalize">{SIDE_LABELS_EN[p.name] ?? p.name}:</span>
          <span className="text-foreground font-bold">{p.value}</span>
        </div>
      ))}
      <div className="border-t border-border mt-1.5 pt-1.5 flex justify-between">
        <span className="text-muted-foreground">Total:</span>
        <span className="text-foreground font-bold">{total}</span>
      </div>
    </div>
  );
}

export default function TimelinePage() {
  const [window, setWindow] = useState<WindowHours>(24);
  const [scrubMode, setScrubMode]   = useState(false);
  const [scrubIdx, setScrubIdx]     = useState(0);
  const [isPlaying, setIsPlaying]   = useState(false);
  const [speedIdx, setSpeedIdx]     = useState<SpeedIdx>(0);
  const playRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const timelineParams = { hours: window };
  const { data, isLoading } = useGetEventsTimeline(
    timelineParams,
    { query: { queryKey: getGetEventsTimelineQueryKey(timelineParams), refetchInterval: 30_000 } },
  );

  const hours = data?.hours ?? [];
  const maxScrub = Math.max(0, hours.length - SCRUB_WINDOW);

  /* Reset scrubber when window changes */
  useEffect(() => {
    setScrubMode(false);
    setScrubIdx(0);
    setIsPlaying(false);
  }, [window]);

  /* Stop play when reaching the end */
  useEffect(() => {
    if (scrubIdx >= maxScrub && isPlaying) {
      setIsPlaying(false);
    }
  }, [scrubIdx, maxScrub, isPlaying]);

  /* Play interval */
  const stopPlay = useCallback(() => {
    if (playRef.current) { clearInterval(playRef.current); playRef.current = null; }
  }, []);

  useEffect(() => {
    if (isPlaying) {
      const ms = SPEEDS[speedIdx].ms;
      playRef.current = setInterval(() => {
        setScrubIdx(prev => {
          if (prev >= maxScrub) { setIsPlaying(false); return prev; }
          return prev + 1;
        });
      }, ms);
    } else {
      stopPlay();
    }
    return stopPlay;
  }, [isPlaying, speedIdx, maxScrub, stopPlay]);

  /* Display slice */
  const displayHours = scrubMode
    ? hours.slice(scrubIdx, scrubIdx + SCRUB_WINDOW)
    : hours;

  /* Derive summary stats from full window (not scrubbed) */
  const totalEvents  = hours.reduce((s, h) => s + h.total, 0);
  const busiest      = hours.reduce(
    (best, h) => (h.total > best.total ? h : best),
    { hour: "", total: 0, red: 0, blue: 0, neutral: 0 },
  );
  const redTotal     = hours.reduce((s, h) => s + h.red, 0);
  const blueTotal    = hours.reduce((s, h) => s + h.blue, 0);
  const neutralTotal = hours.reduce((s, h) => s + h.neutral, 0);

  /* Window label for scrubber */
  const scrubStartLabel = hours[scrubIdx]
    ? new Date(hours[scrubIdx].hour).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })
    : "";
  const scrubEndLabel = hours[Math.min(scrubIdx + SCRUB_WINDOW - 1, hours.length - 1)]
    ? new Date(hours[Math.min(scrubIdx + SCRUB_WINDOW - 1, hours.length - 1)].hour).toLocaleString([], { hour: "2-digit", minute: "2-digit" })
    : "";

  return (
    <Layout>
      <div className="p-6 h-full flex flex-col gap-5 overflow-hidden">

        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-primary" />
            <h2 className="text-2xl font-bold font-mono tracking-tight uppercase">
              Activity Timeline
            </h2>
          </div>

          {/* Window selector */}
          <div className="flex items-center gap-1 bg-card border border-border rounded-md p-1">
            {WINDOWS.map(w => (
              <button
                key={w.value}
                onClick={() => setWindow(w.value)}
                className={`px-3 py-0.5 rounded text-[10px] font-mono font-bold uppercase transition-colors ${
                  window === w.value
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >{w.label}</button>
            ))}
          </div>
        </div>

        {/* ── Summary Stats ───────────────────────────────────────────── */}
        {!isLoading && (
          <div className="grid grid-cols-4 gap-3 shrink-0">
            {[
              { label: "Total Events",       value: totalEvents,   color: "text-foreground"   },
              { label: "Adversary",          value: redTotal,      color: "text-red-400"       },
              { label: "IDF / Blue",         value: blueTotal,     color: "text-blue-400"      },
              { label: "Neutral",            value: neutralTotal,  color: "text-slate-400"     },
            ].map(stat => (
              <div key={stat.label} className="bg-card border border-border rounded-md p-4">
                <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-1">
                  {stat.label}
                </p>
                <p className={`text-3xl font-bold font-mono ${stat.color}`}>
                  {stat.value}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* ── Chart ───────────────────────────────────────────────────── */}
        <div className="flex-1 bg-card border border-border rounded-md p-4 min-h-0">
          {isLoading ? (
            <div className="h-full flex items-center justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : totalEvents === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-3 text-muted-foreground">
              <Clock className="w-12 h-12 opacity-20" />
              <p className="font-mono text-sm">No events in this window</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={displayHours}
                margin={{ top: 4, right: 8, left: -16, bottom: 40 }}
                barCategoryGap="20%"
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="hsl(var(--border))"
                  vertical={false}
                />
                <XAxis
                  dataKey="hour"
                  tickFormatter={h => formatHour(h, window)}
                  tick={{ fontSize: 9, fontFamily: "monospace", fill: "hsl(var(--muted-foreground))" }}
                  angle={-45}
                  textAnchor="end"
                  interval={scrubMode ? 0 : Math.ceil(displayHours.length / 16)}
                  stroke="hsl(var(--border))"
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 9, fontFamily: "monospace", fill: "hsl(var(--muted-foreground))" }}
                  stroke="hsl(var(--border))"
                />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: "hsl(var(--muted)/0.3)" }} />
                <Legend
                  formatter={(v) => (
                    <span style={{ fontSize: 10, fontFamily: "monospace", color: "hsl(var(--muted-foreground))" }}>
                      {SIDE_LABELS_EN[v] ?? v}
                    </span>
                  )}
                  wrapperStyle={{ paddingTop: 8 }}
                />
                <Bar dataKey="red"     stackId="a" fill={SIDE_CHART_COLORS.red}     radius={[0, 0, 0, 0]} name="red" />
                <Bar dataKey="blue"    stackId="a" fill={SIDE_CHART_COLORS.blue}    radius={[0, 0, 0, 0]} name="blue" />
                <Bar dataKey="neutral" stackId="a" fill={SIDE_CHART_COLORS.neutral} radius={[2, 2, 0, 0]} name="neutral" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* ── Playback Scrubber ────────────────────────────────────────── */}
        {!isLoading && hours.length > SCRUB_WINDOW && (
          <div className="bg-card border border-border rounded-md px-4 py-3 shrink-0 space-y-2">
            {/* Controls row */}
            <div className="flex items-center gap-3">
              {/* Enable/disable scrub mode */}
              <button
                onClick={() => { setScrubMode(v => !v); setIsPlaying(false); setScrubIdx(0); }}
                className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border transition-colors ${
                  scrubMode
                    ? "bg-primary/20 border-primary/50 text-primary"
                    : "border-border text-muted-foreground hover:border-primary/40 hover:text-primary"
                }`}
              >
                {scrubMode ? "EXIT PLAYBACK" : "▶ PLAYBACK"}
              </button>

              {scrubMode && (
                <>
                  {/* Reset */}
                  <button
                    onClick={() => { setScrubIdx(0); setIsPlaying(false); }}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                    title="Reset to start"
                  >
                    <SkipBack className="w-4 h-4" />
                  </button>

                  {/* Play/Pause */}
                  <button
                    onClick={() => setIsPlaying(v => !v)}
                    disabled={scrubIdx >= maxScrub}
                    className={`flex items-center gap-1 text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border transition-colors disabled:opacity-40 ${
                      isPlaying
                        ? "bg-red-500/20 border-red-500/50 text-red-400"
                        : "bg-emerald-500/20 border-emerald-500/50 text-emerald-400"
                    }`}
                  >
                    {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
                    {isPlaying ? "PAUSE" : "PLAY"}
                  </button>

                  {/* Speed toggle */}
                  <button
                    onClick={() => { setSpeedIdx(i => (i === 0 ? 1 : 0) as SpeedIdx); }}
                    className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded border border-border text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {SPEEDS[speedIdx].label}
                  </button>

                  {/* Current window label */}
                  {scrubStartLabel && (
                    <span className="text-[10px] font-mono text-muted-foreground ml-auto">
                      <span className="text-foreground font-bold">{scrubStartLabel}</span>
                      {scrubEndLabel && ` → ${scrubEndLabel}`}
                      <span className="text-muted-foreground/60"> ({SCRUB_WINDOW}h window)</span>
                    </span>
                  )}
                </>
              )}
            </div>

            {/* Range slider */}
            {scrubMode && (
              <div className="flex items-center gap-3">
                <span className="text-[9px] font-mono text-muted-foreground shrink-0">
                  {hours[0] ? new Date(hours[0].hour).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit" }) : ""}
                </span>
                <input
                  type="range"
                  min={0}
                  max={maxScrub}
                  value={scrubIdx}
                  onChange={e => { setScrubIdx(Number(e.target.value)); setIsPlaying(false); }}
                  className="flex-1 h-1.5 accent-primary cursor-pointer"
                />
                <span className="text-[9px] font-mono text-muted-foreground shrink-0">
                  {hours[hours.length - 1] ? new Date(hours[hours.length - 1].hour).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit" }) : ""}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Busiest hour callout */}
        {!isLoading && busiest.total > 0 && !scrubMode && (
          <p className="text-[10px] font-mono text-muted-foreground shrink-0">
            Peak activity:{" "}
            <span className="text-foreground font-bold">
              {new Date(busiest.hour).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
            </span>{" "}
            · {busiest.total} events
          </p>
        )}

      </div>
    </Layout>
  );
}
