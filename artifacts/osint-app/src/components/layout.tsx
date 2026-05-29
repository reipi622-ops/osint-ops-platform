import { type ReactNode, useEffect, useState } from "react";
import { Link, useLocation } from "wouter";
import { Map, LayoutDashboard, List, Rss, MessageSquare, Bell, Clock, Shield } from "lucide-react";
import {
  useGetTelegramAuthStatus, getGetTelegramAuthStatusQueryKey,
  useListAlerts, getListAlertsQueryKey,
} from "@workspace/api-client-react";

const NAV_ITEMS = [
  { href: "/",          label: "מפה חיה",       icon: Map },
  { href: "/dashboard", label: "תמונת מצב",      icon: LayoutDashboard },
  { href: "/events",    label: "אירועים",         icon: List },
  { href: "/alerts",    label: "התרעות",          icon: Bell,          isAlerts: true },
  { href: "/timeline",  label: "ציר זמן",         icon: Clock },
  { href: "/sources",   label: "מקורות",          icon: Rss },
  { href: "/telegram",  label: "ניטור טלגרם",     icon: MessageSquare, isTelegram: true },
] as const;

function IsraelClock() {
  const [time, setTime] = useState("");
  const [date, setDate] = useState("");

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(now.toLocaleTimeString("he-IL", {
        timeZone: "Asia/Jerusalem",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      }));
      setDate(now.toLocaleDateString("he-IL", {
        timeZone: "Asia/Jerusalem",
        weekday: "short",
        day: "numeric",
        month: "short",
      }));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="px-4 py-2.5 border-b border-border/60 bg-card/50">
      <div className="flex items-center gap-2 justify-between">
        <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-widest">שעון ישראל</span>
        <div className="text-right">
          <div className="text-sm font-mono font-bold text-foreground tabular-nums">{time}</div>
          <div className="text-[9px] text-muted-foreground">{date}</div>
        </div>
      </div>
    </div>
  );
}

export function Layout({ children }: { children: ReactNode }) {
  const [location] = useLocation();

  const { data: telegramStatus } = useGetTelegramAuthStatus({
    query: { queryKey: getGetTelegramAuthStatusQueryKey(), refetchInterval: 10000 },
  });

  const { data: alertsData } = useListAlerts(
    { limit: 1 },
    { query: { queryKey: getListAlertsQueryKey({ limit: 1 }), refetchInterval: 15000 } },
  );

  const alertCount = alertsData?.total ?? 0;

  const telegramDot = telegramStatus?.authorized
    ? "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.5)]"
    : telegramStatus?.configured
    ? "bg-yellow-500 shadow-[0_0_6px_rgba(234,179,8,0.5)]"
    : "bg-slate-600";

  return (
    <div className="flex h-screen w-full bg-background text-foreground overflow-hidden">
      <aside className="w-60 border-l border-border/60 bg-card flex flex-col shrink-0">

        {/* Brand */}
        <div className="px-5 py-4 border-b border-border/60">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0">
              <Shield className="w-3.5 h-3.5 text-primary" />
            </div>
            <div>
              <h1 className="text-sm font-bold tracking-tight text-foreground leading-none">
                OSINT OPS
              </h1>
              <p className="text-[10px] text-muted-foreground mt-0.5">
                מרכז הייכון
              </p>
            </div>
          </div>
        </div>

        {/* Israel Clock */}
        <IsraelClock />

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map((item) => {
            const isActive = location === item.href;
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} className="block">
                <div
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group ${
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 transition-colors ${isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"}`} />
                  <span className="flex-1 text-sm font-medium">{item.label}</span>

                  {"isTelegram" in item && (
                    <span className={`w-2 h-2 rounded-full shrink-0 ${telegramDot}`} />
                  )}

                  {"isAlerts" in item && alertCount > 0 && (
                    <span className="shrink-0 min-w-[18px] h-[18px] rounded-full bg-orange-500 text-white text-[9px] font-mono font-bold flex items-center justify-center px-1">
                      {alertCount > 99 ? "99+" : alertCount}
                    </span>
                  )}
                </div>
              </Link>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border/60">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse shrink-0" />
            <span className="text-[11px] text-muted-foreground font-mono">מצב: פעיל</span>
          </div>
        </div>
      </aside>

      <main className="flex-1 relative overflow-hidden flex flex-col min-w-0">
        {children}
      </main>
    </div>
  );
}
