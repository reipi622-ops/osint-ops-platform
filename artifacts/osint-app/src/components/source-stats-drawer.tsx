import { X, Zap, Clock, BarChart2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  useGetSourceStats,
  getGetSourceStatsQueryKey,
} from "@workspace/api-client-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

interface SourceStatsDrawerProps {
  sourceId: number | null;
  sourceName?: string;
  onClose: () => void;
}

const TOOLTIP_STYLE = {
  contentStyle: { backgroundColor: "#020817", borderColor: "#1e293b" },
  labelStyle: { color: "#94a3b8", fontSize: 10, fontFamily: "monospace" },
  itemStyle: { color: "#f8fafc", fontSize: 10, fontFamily: "monospace" },
};

function formatSeconds(sec?: number | null): string {
  if (sec == null) return "—";
  if (sec < 60) return `${sec.toFixed(0)}s`;
  if (sec < 3600) return `${(sec / 60).toFixed(0)}m`;
  return `${(sec / 3600).toFixed(1)}h`;
}

function reliabilityColor(score: number): string {
  if (score >= 0.75) return "bg-emerald-500";
  if (score >= 0.5) return "bg-yellow-500";
  return "bg-red-500";
}

function reliabilityLabel(score: number): string {
  if (score >= 0.75) return "HIGH";
  if (score >= 0.5) return "MED";
  return "LOW";
}

function reliabilityBadgeClass(score: number): string {
  if (score >= 0.75) return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
  if (score >= 0.5) return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
  return "bg-red-500/20 text-red-400 border-red-500/30";
}

export function SourceStatsDrawer({ sourceId, sourceName, onClose }: SourceStatsDrawerProps) {
  const isOpen = sourceId != null;

  const { data: stats, isLoading } = useGetSourceStats(
    sourceId ?? 0,
    {
      query: {
        queryKey: getGetSourceStatsQueryKey(sourceId ?? 0),
        enabled: sourceId != null,
      },
    },
  );

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-[1100] bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      <div
        className={`fixed inset-y-0 right-0 z-[1200] w-[520px] max-w-[96vw] bg-background border-l border-border shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-border flex items-center justify-between shrink-0 bg-muted/20">
          <div>
            <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-0.5">
              Source Intelligence
            </p>
            <h2 className="text-lg font-bold font-mono truncate max-w-[380px]">
              {sourceName ?? "Source"}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {isLoading ? (
            <div className="space-y-3">
              {Array(4).fill(0).map((_, i) => (
                <div key={i} className="h-12 rounded bg-muted/40 animate-pulse" />
              ))}
            </div>
          ) : !stats ? (
            <p className="text-sm font-mono text-muted-foreground text-center mt-8">
              No statistics available
            </p>
          ) : (
            <>
              {/* ── Summary Stats ── */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-card border border-border rounded-md p-3">
                  <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-1">Total Events</p>
                  <p className="text-2xl font-bold font-mono">{stats.total_events.toLocaleString()}</p>
                </div>
                <div className="bg-card border border-border rounded-md p-3">
                  <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-1">Reliability</p>
                  <div className="flex items-center gap-2">
                    <p className="text-2xl font-bold font-mono">{(stats.reliability_score * 100).toFixed(0)}%</p>
                    <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${reliabilityBadgeClass(stats.reliability_score)}`}>
                      {reliabilityLabel(stats.reliability_score)}
                    </span>
                  </div>
                </div>
                <div className="bg-card border border-border rounded-md p-3">
                  <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-1">Avg Confidence</p>
                  <p className="text-2xl font-bold font-mono">{(stats.avg_confidence * 100).toFixed(0)}%</p>
                </div>
                <div className="bg-card border border-border rounded-md p-3">
                  <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest mb-1">Avg Propaganda</p>
                  <p className={`text-2xl font-bold font-mono ${stats.avg_propaganda >= 0.5 ? "text-red-400" : stats.avg_propaganda >= 0.3 ? "text-yellow-400" : "text-emerald-400"}`}>
                    {(stats.avg_propaganda * 100).toFixed(0)}%
                  </p>
                </div>
              </div>

              {/* ── First-Report Badge ── */}
              {stats.avg_first_report_seconds != null && (
                <div className="flex items-center gap-2 bg-violet-500/10 border border-violet-500/20 rounded-md px-3 py-2">
                  <Zap className="w-4 h-4 text-violet-400 shrink-0" />
                  <div>
                    <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Fastest First-Reporter</p>
                    <p className="text-sm font-mono font-bold text-violet-300">
                      Avg {formatSeconds(stats.avg_first_report_seconds)} ahead
                    </p>
                  </div>
                </div>
              )}

              {/* ── Source Type ── */}
              <div className="flex items-center gap-2">
                <span className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Channel Type:</span>
                <Badge variant="outline" className="font-mono text-[10px] uppercase">
                  {stats.source_type}
                </Badge>
                <span className="text-[9px] font-mono text-muted-foreground ml-2 uppercase tracking-widest">Important Events:</span>
                <span className="text-[10px] font-mono font-bold text-orange-400">{stats.important_events}</span>
              </div>

              {/* ── Confidence Line Chart ── */}
              {stats.reliability_history.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <BarChart2 className="w-3 h-3 text-muted-foreground" />
                    <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Avg Confidence — 14 Days</p>
                  </div>
                  <div className="bg-card border border-border rounded-md p-3 h-[130px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={stats.reliability_history} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 8, fontFamily: "monospace", fill: "#64748b" }}
                          tickFormatter={d => new Date(d).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                          stroke="#1e293b"
                        />
                        <YAxis
                          domain={[0, 1]}
                          tick={{ fontSize: 8, fontFamily: "monospace", fill: "#64748b" }}
                          tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                          stroke="#1e293b"
                        />
                        <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [`${(v * 100).toFixed(0)}%`, "Confidence"]} />
                        <Line type="monotone" dataKey="avg_confidence" stroke="#3b82f6" strokeWidth={1.5} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* ── Propaganda Trend Line Chart ── */}
              {stats.propaganda_trend.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <BarChart2 className="w-3 h-3 text-muted-foreground" />
                    <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Propaganda Score — 14 Days</p>
                  </div>
                  <div className="bg-card border border-border rounded-md p-3 h-[130px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={stats.propaganda_trend} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis
                          dataKey="date"
                          tick={{ fontSize: 8, fontFamily: "monospace", fill: "#64748b" }}
                          tickFormatter={d => new Date(d).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                          stroke="#1e293b"
                        />
                        <YAxis
                          domain={[0, 1]}
                          tick={{ fontSize: 8, fontFamily: "monospace", fill: "#64748b" }}
                          tickFormatter={v => `${(v * 100).toFixed(0)}%`}
                          stroke="#1e293b"
                        />
                        <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [`${(v * 100).toFixed(0)}%`, "Propaganda"]} />
                        <Line type="monotone" dataKey="avg_propaganda" stroke="#f59e0b" strokeWidth={1.5} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* ── Hourly Activity Bar Chart ── */}
              {stats.hourly_activity.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-3 h-3 text-muted-foreground" />
                    <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">Hourly Activity (UTC)</p>
                  </div>
                  <div className="bg-card border border-border rounded-md p-3 h-[130px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={stats.hourly_activity} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                        <XAxis
                          dataKey="hour"
                          tick={{ fontSize: 8, fontFamily: "monospace", fill: "#64748b" }}
                          tickFormatter={h => `${String(h).padStart(2, "0")}:00`}
                          stroke="#1e293b"
                          interval={3}
                        />
                        <YAxis
                          allowDecimals={false}
                          tick={{ fontSize: 8, fontFamily: "monospace", fill: "#64748b" }}
                          stroke="#1e293b"
                        />
                        <Tooltip {...TOOLTIP_STYLE} formatter={(v: number) => [v, "Events"]} labelFormatter={h => `${String(h).padStart(2, "0")}:00`} />
                        <Bar dataKey="count" fill="#3b82f6" radius={[2, 2, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Reliability bar */}
              <div className="space-y-1 border-t border-border pt-4">
                <div className="flex justify-between text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
                  <span>Reliability Score</span>
                  <span>{(stats.reliability_score * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${reliabilityColor(stats.reliability_score)}`}
                    style={{ width: `${stats.reliability_score * 100}%` }}
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
