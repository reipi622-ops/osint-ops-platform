import { X, MapPin, CheckCheck, Radio, Image, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { EscalationBadge } from "@/components/escalation-badge";
import {
  SIDE_COLORS, SIDE_LABELS_EN, CATEGORY_COLORS, IMPORTANCE_TAG_LABELS,
  CONFIDENCE_LEVEL_COLORS, CONFIDENCE_LEVEL_LABELS, CONFIDENCE_LEVEL_TEXT_COLORS,
} from "@/lib/constants";
import type { EventResponse } from "@workspace/api-client-react";
import { useState } from "react";

interface EventDrawerProps {
  event: EventResponse | null;
  onClose: () => void;
}

function reliabilityFromSource(sourceName?: string | null): number {
  if (!sourceName) return 0.5;
  const l = sourceName.toLowerCase();
  if (l.includes("telegram")) return 0.85;
  if (l.includes("rss") || l.includes("news")) return 0.60;
  return 0.55;
}

function ConfidenceLevelBadge({ level }: { level?: string | null }) {
  const l = level || "low";
  const label = CONFIDENCE_LEVEL_LABELS[l] ?? l.toUpperCase();
  const colorClass = CONFIDENCE_LEVEL_COLORS[l] ?? "bg-slate-500";

  const icon =
    l === "verified" ? <CheckCheck className="w-3 h-3" /> :
    l === "high"     ? <Radio className="w-3 h-3" /> :
    l === "medium"   ? <AlertTriangle className="w-3 h-3" /> :
    null;

  return (
    <Badge className={`text-[10px] font-mono border-none text-white shrink-0 inline-flex items-center gap-1 ${colorClass}`}>
      {icon}
      {label}
    </Badge>
  );
}

export function EventDrawer({ event, onClose }: EventDrawerProps) {
  const [showRaw, setShowRaw] = useState(false);

  const isOpen = !!event;
  const tags = event?.importance_tags
    ? event.importance_tags.split(",").filter(Boolean)
    : [];
  const reliability = reliabilityFromSource(event?.source_name);
  const propagandaScore = event?.propaganda_score ?? 0;
  const confirmationCount = event?.confirmation_count ?? 0;
  const confirmingSources = event?.confirming_sources
    ? event.confirming_sources.split(",").filter(Boolean)
    : [];

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-[1100] bg-black/50 backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* Slide-in panel */}
      <div
        className={`fixed inset-y-0 right-0 z-[1200] w-[480px] max-w-[96vw] bg-background border-l border-border shadow-2xl flex flex-col transition-transform duration-300 ease-in-out ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        {event && (
          <>
            {/* ── Header ─────────────────────────────────────────────── */}
            <div
              className={`p-4 border-b border-border flex items-start gap-3 shrink-0 ${
                event.side === "red"
                  ? "bg-red-950/40"
                  : event.side === "blue"
                  ? "bg-blue-950/40"
                  : "bg-muted/20"
              }`}
            >
              <div className="flex-1 flex flex-wrap gap-1.5 items-center min-w-0">
                <Badge
                  className={`text-[10px] font-mono border-none text-white shrink-0 ${
                    SIDE_COLORS[event.side ?? "neutral"] || SIDE_COLORS.neutral
                  }`}
                >
                  {SIDE_LABELS_EN[event.side ?? "neutral"] ?? "Neutral"}
                </Badge>
                <Badge
                  className={`text-[10px] font-mono border-none text-white shrink-0 uppercase ${
                    CATEGORY_COLORS[event.category] || CATEGORY_COLORS.other
                  }`}
                >
                  {event.category}
                </Badge>
                <ConfidenceLevelBadge level={event.confidence_level} />
                {event.is_important && (
                  <Badge className="text-[10px] font-mono border-none bg-orange-500 text-white shrink-0 animate-pulse">
                    ⚠ ALERT
                  </Badge>
                )}
                {event.has_media && (
                  <Badge className="text-[10px] font-mono border-none bg-sky-600 text-white shrink-0 inline-flex items-center gap-1">
                    <Image className="w-2.5 h-2.5" />
                    MEDIA
                  </Badge>
                )}
                <span className="text-[9px] font-mono text-muted-foreground ml-auto shrink-0">
                  #{event.id}
                </span>
              </div>
              <button
                onClick={onClose}
                className="text-muted-foreground hover:text-foreground transition-colors shrink-0 mt-0.5"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* ── Body ───────────────────────────────────────────────── */}
            <div className="flex-1 overflow-y-auto p-4 space-y-5">

              {/* Importance tags */}
              {tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {tags.map((tag) => {
                    const meta = IMPORTANCE_TAG_LABELS[tag];
                    return (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-mono bg-orange-500/15 text-orange-400 border border-orange-500/30"
                      >
                        {meta?.icon ?? "▲"}{" "}
                        <span dir="rtl">{meta?.label ?? tag}</span>
                      </span>
                    );
                  })}
                </div>
              )}

              {/* Hebrew title */}
              <div className="space-y-1">
                <p
                  className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest"
                  dir="ltr"
                >
                  כותרת
                </p>
                <h2
                  className="text-lg font-bold leading-snug"
                  dir="rtl"
                >
                  {event.title_he || event.title}
                </h2>
              </div>

              {/* Hebrew description */}
              {event.description_he && (
                <div className="space-y-1">
                  <p
                    className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest"
                    dir="ltr"
                  >
                    תיאור
                  </p>
                  <p
                    className="text-sm text-muted-foreground leading-relaxed"
                    dir="rtl"
                  >
                    {event.description_he}
                  </p>
                </div>
              )}

              {/* Metadata grid */}
              <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs font-mono">
                <div className="space-y-0.5">
                  <p className="text-[9px] text-muted-foreground uppercase tracking-widest">
                    LOCATION
                  </p>
                  <p className="flex items-center gap-1 text-foreground truncate">
                    <MapPin className="w-3 h-3 text-muted-foreground shrink-0" />
                    {event.location_name || "—"}
                  </p>
                </div>

                <div className="space-y-0.5">
                  <p className="text-[9px] text-muted-foreground uppercase tracking-widest">
                    TIME (UTC)
                  </p>
                  <p className="text-foreground">
                    {new Date(event.created_at).toLocaleString([], {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>

                <div className="space-y-0.5 col-span-2">
                  <p className="text-[9px] text-muted-foreground uppercase tracking-widest">
                    SOURCE
                  </p>
                  <p className="text-sm font-semibold truncate">
                    {event.source_name
                      ? event.source_name.replace(/^Telegram:\s*/i, "").replace(/^@/, "")
                      : "לא ידוע"}
                  </p>
                </div>
              </div>

              {/* ── Intelligence Panel ──────────────────────────────── */}
              <div className="border border-border rounded-md overflow-hidden">
                <div className="px-3 py-2 bg-muted/30 border-b border-border">
                  <p className="text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
                    Intelligence Assessment
                  </p>
                </div>
                <div className="p-3 space-y-3">

                  {/* Confidence level */}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-muted-foreground uppercase">Intel Level</span>
                    <ConfidenceLevelBadge level={event.confidence_level} />
                  </div>

                  {/* Escalation level */}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-muted-foreground uppercase">Escalation</span>
                    <EscalationBadge level={event.escalation_level} />
                  </div>

                  {/* Confirmation count */}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-muted-foreground uppercase">Confirmations</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] font-mono font-bold text-foreground">
                        {confirmationCount}
                      </span>
                      {confirmationCount >= 2 && (
                        <CheckCheck className="w-3.5 h-3.5 text-violet-400" />
                      )}
                    </div>
                  </div>

                  {/* Confirming sources list */}
                  {confirmingSources.length > 0 && (
                    <div className="space-y-1">
                      <p className="text-[9px] font-mono text-muted-foreground uppercase">Corroborated by</p>
                      <div className="flex flex-wrap gap-1">
                        {confirmingSources.map((src) => (
                          <span
                            key={src}
                            className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-violet-500/10 text-violet-400 border border-violet-500/20"
                          >
                            {src}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Media evidence */}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-muted-foreground uppercase">Media Evidence</span>
                    <span className={`text-[10px] font-mono font-bold ${event.has_media ? "text-sky-400" : "text-muted-foreground"}`}>
                      {event.has_media ? "Yes" : "None"}
                    </span>
                  </div>

                  {/* Propaganda risk bar */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
                      <span>Propaganda Risk</span>
                      <span className={
                        propagandaScore >= 0.6 ? "text-red-400" :
                        propagandaScore >= 0.3 ? "text-yellow-400" :
                        "text-emerald-400"
                      }>
                        {propagandaScore >= 0.6 ? "HIGH" : propagandaScore >= 0.3 ? "MED" : "LOW"}
                        {" "}({(propagandaScore * 100).toFixed(0)}%)
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${
                          propagandaScore >= 0.6 ? "bg-red-500" :
                          propagandaScore >= 0.3 ? "bg-yellow-500" :
                          "bg-emerald-500"
                        }`}
                        style={{ width: `${propagandaScore * 100}%` }}
                      />
                    </div>
                  </div>

                </div>
              </div>

              {/* ── Signal Meters ────────────────────────────────────── */}
              <div className="space-y-3 border-t border-border pt-4">
                <div className="space-y-1">
                  <div className="flex justify-between text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
                    <span>CONFIDENCE</span>
                    <span>{(event.confidence * 100).toFixed(0)}%</span>
                  </div>
                  <Progress value={event.confidence * 100} className="h-1.5" />
                </div>

                {event.is_important && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
                      <span>THREAT SCORE</span>
                      <span>{((event.importance_score ?? 0) * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                      <div
                        className="h-full rounded-full bg-orange-500 transition-all"
                        style={{ width: `${(event.importance_score ?? 0) * 100}%` }}
                      />
                    </div>
                  </div>
                )}

                <div className="space-y-1">
                  <div className="flex justify-between text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
                    <span>SOURCE RELIABILITY</span>
                    <span>{(reliability * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-secondary overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        reliability >= 0.8
                          ? "bg-emerald-500"
                          : reliability >= 0.6
                          ? "bg-yellow-500"
                          : "bg-red-500"
                      }`}
                      style={{ width: `${reliability * 100}%` }}
                    />
                  </div>
                </div>
              </div>

              {/* Raw text collapsible */}
              {event.raw_text && (
                <div className="border border-border rounded-md overflow-hidden">
                  <button
                    onClick={() => setShowRaw((v) => !v)}
                    className="w-full flex items-center justify-between px-3 py-2 text-[9px] font-mono text-muted-foreground uppercase tracking-widest hover:bg-muted/40 transition-colors"
                  >
                    <span>
                      ORIGINAL TEXT ({(event.original_lang ?? "ar").toUpperCase()})
                    </span>
                    <span className="text-[10px]">{showRaw ? "▲" : "▼"}</span>
                  </button>
                  {showRaw && (
                    <div
                      dir="rtl"
                      className="p-3 bg-muted/20 border-t border-border"
                    >
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {event.raw_text}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Footer */}
              <p className="text-[9px] font-mono text-muted-foreground/40" dir="ltr">
                HASH: {event.event_hash}
              </p>
            </div>
          </>
        )}
      </div>
    </>
  );
}
