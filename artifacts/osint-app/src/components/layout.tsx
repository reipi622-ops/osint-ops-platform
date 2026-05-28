import { type ReactNode } from "react";
import { Link, useLocation } from "wouter";
import { Map, LayoutDashboard, List, Rss, MessageSquare, Bell, Clock } from "lucide-react";
import {
  useGetTelegramAuthStatus, getGetTelegramAuthStatusQueryKey,
  useListAlerts, getListAlertsQueryKey,
} from "@workspace/api-client-react";

export function Layout({ children }: { children: ReactNode }) {
  const [location] = useLocation();

  const { data: telegramStatus } = useGetTelegramAuthStatus({
    query: { queryKey: getGetTelegramAuthStatusQueryKey(), refetchInterval: 10000 },
  });

  const { data: alertsData } = useListAlerts(
    { limit: 1 },
    { query: { queryKey: getListAlertsQueryKey({ limit: 1 }), refetchInterval: 15000 } },
  );

  const getTelegramStatusDot = () => {
    if (telegramStatus?.authorized) return "bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]";
    if (telegramStatus?.configured) return "bg-yellow-500 shadow-[0_0_8px_rgba(234,179,8,0.6)]";
    return "bg-slate-500";
  };

  const alertCount = alertsData?.total ?? 0;

  const navItems = [
    { href: "/",         label: "Live Map",  icon: Map },
    { href: "/dashboard",label: "Dashboard", icon: LayoutDashboard },
    { href: "/events",   label: "Events",    icon: List },
    { href: "/alerts",   label: "Alerts",    icon: Bell,         alertBadge: alertCount > 0 },
    { href: "/timeline", label: "Timeline",  icon: Clock },
    { href: "/sources",  label: "Sources",   icon: Rss },
    { href: "/telegram", label: "Telegram",  icon: MessageSquare, badge: getTelegramStatusDot() },
  ];

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      <aside className="w-64 border-r border-border bg-card flex flex-col">
        <div className="p-4 border-b border-border">
          <h1 className="text-xl font-bold tracking-tight text-primary flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-destructive animate-pulse" />
            OSINT OPS
          </h1>
          <p className="text-xs text-muted-foreground mt-1 uppercase tracking-widest font-mono">
            Middle East Region
          </p>
        </div>
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location === item.href;
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className="block">
                <div
                  className={`flex items-center gap-3 px-3 py-2 rounded-md transition-colors ${
                    isActive
                      ? "bg-primary/10 text-primary font-medium"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  }`}
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span className="flex-1 text-sm">{item.label}</span>
                  {/* Status dot (Telegram) */}
                  {item.badge && !item.alertBadge && (
                    <span className={`w-2 h-2 rounded-full shrink-0 ${item.badge}`} />
                  )}
                  {/* Alert count badge */}
                  {item.alertBadge && alertCount > 0 && (
                    <span className="shrink-0 min-w-[18px] h-[18px] rounded-full bg-orange-500 text-white text-[9px] font-mono font-bold flex items-center justify-center px-1">
                      {alertCount > 99 ? "99+" : alertCount}
                    </span>
                  )}
                </div>
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-border text-xs text-muted-foreground font-mono">
          SYSTEM: ONLINE<br />
          DEFCON: 3
        </div>
      </aside>
      <main className="flex-1 relative overflow-hidden flex flex-col">
        {children}
      </main>
    </div>
  );
}
