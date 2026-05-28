import { Layout } from "@/components/layout";
import { useGetDashboardStats, useListPatterns, getListPatternsQueryKey } from "@workspace/api-client-react";
import type { PatternAlert } from "@workspace/api-client-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, AlertTriangle, Layers, TrendingUp, Network, Zap, ShieldAlert } from "lucide-react";
import { CATEGORY_HEX_COLORS } from "@/lib/constants";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
} from "recharts";

function patternTypeIcon(type: string) {
  if (type === "spike")       return <TrendingUp className="w-3.5 h-3.5 shrink-0" />;
  if (type === "escalation")  return <ShieldAlert className="w-3.5 h-3.5 shrink-0" />;
  if (type === "coordinated") return <Network className="w-3.5 h-3.5 shrink-0" />;
  return <Zap className="w-3.5 h-3.5 shrink-0" />;
}

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-600 text-white",
  high:     "bg-orange-500 text-white",
  medium:   "bg-yellow-500 text-black",
  low:      "bg-slate-500 text-white",
};

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diffMs / 60_000);
  if (m < 1)   return "just now";
  if (m < 60)  return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function PatternRow({ p }: { p: PatternAlert }) {
  return (
    <div className="flex items-start gap-2 py-2 border-b border-border last:border-0">
      <span className="text-muted-foreground mt-0.5">{patternTypeIcon(p.type)}</span>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-mono text-foreground leading-snug truncate">{p.description}</p>
        {p.location_hint && (
          <p className="text-[9px] font-mono text-muted-foreground truncate">{p.location_hint}</p>
        )}
      </div>
      <div className="flex flex-col items-end gap-1 shrink-0">
        <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded uppercase font-bold ${SEVERITY_BADGE[p.severity] ?? SEVERITY_BADGE.low}`}>
          {p.severity}
        </span>
        <span className="text-[9px] font-mono text-muted-foreground">{relativeTime(p.detected_at)}</span>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: stats, isLoading } = useGetDashboardStats();
  const { data: patternsData } = useListPatterns({
    query: {
      queryKey: getListPatternsQueryKey(),
      refetchInterval: 20_000,
    },
  });

  const patterns = (patternsData?.patterns ?? []).slice(0, 6);

  if (isLoading) {
    return (
      <Layout>
        <div className="flex h-full items-center justify-center">
          <Activity className="w-8 h-8 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  if (!stats) return <Layout><div>Error loading stats</div></Layout>;

  return (
    <Layout>
      <div className="p-6 h-full overflow-y-auto bg-background">
        <h2 className="text-2xl font-bold mb-6 font-mono tracking-tight">OPERATIONAL OVERVIEW</h2>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium uppercase text-muted-foreground">Total Events</CardTitle>
              <Layers className="w-4 h-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.total_events}</div>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium uppercase text-muted-foreground">Events Today</CardTitle>
              <AlertTriangle className="w-4 h-4 text-destructive" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.events_today}</div>
            </CardContent>
          </Card>
          <Card className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
              <CardTitle className="text-sm font-medium uppercase text-muted-foreground">Events This Week</CardTitle>
              <Activity className="w-4 h-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">{stats.events_this_week}</div>
            </CardContent>
          </Card>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-sm uppercase text-muted-foreground font-mono">Category Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={stats.by_category}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="count"
                    nameKey="category"
                  >
                    {stats.by_category.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={CATEGORY_HEX_COLORS[entry.category] || CATEGORY_HEX_COLORS.other} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#020817', borderColor: '#1e293b' }}
                    itemStyle={{ color: '#f8fafc' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle className="text-sm uppercase text-muted-foreground font-mono">14-Day Timeline</CardTitle>
            </CardHeader>
            <CardContent className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={stats.recent_timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} tickFormatter={(val) => new Date(val).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#020817', borderColor: '#1e293b' }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Line type="monotone" dataKey="count" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: '#3b82f6' }} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>

        {/* ── Live Patterns Card ──────────────────────────────────────── */}
        <Card className="bg-card border-border">
          <CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
            <CardTitle className="text-sm uppercase text-muted-foreground font-mono flex items-center gap-2">
              <Zap className="w-4 h-4 text-yellow-400" />
              Live Patterns
            </CardTitle>
            {patternsData && (
              <Badge variant="outline" className="font-mono text-[10px]">
                {patternsData.total} active
              </Badge>
            )}
          </CardHeader>
          <CardContent>
            {patterns.length === 0 ? (
              <p className="text-sm font-mono text-muted-foreground text-center py-4">
                No active patterns detected
              </p>
            ) : (
              <div>
                {patterns.map((p, i) => (
                  <PatternRow key={`${p.type}-${p.detected_at}-${i}`} p={p} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
