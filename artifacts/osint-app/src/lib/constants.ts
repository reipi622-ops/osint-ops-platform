export const CATEGORY_COLORS: Record<string, string> = {
  military: "bg-red-500",
  political: "bg-blue-500",
  humanitarian: "bg-emerald-500",
  crime: "bg-amber-500",
  accident: "bg-yellow-500",
  other: "bg-slate-500",
};

export const CATEGORY_TEXT_COLORS: Record<string, string> = {
  military: "text-red-500",
  political: "text-blue-500",
  humanitarian: "text-emerald-500",
  crime: "text-amber-500",
  accident: "text-yellow-500",
  other: "text-slate-500",
};

export const CATEGORY_HEX_COLORS: Record<string, string> = {
  military: "#ef4444",
  political: "#3b82f6",
  humanitarian: "#10b981",
  crime: "#f59e0b",
  accident: "#eab308",
  other: "#64748b",
};

// ── Side (Red / Blue / Neutral) ───────────────────────────────────────────────
export const SIDE_LABELS: Record<string, string> = {
  red: "Red Side",
  blue: "Blue Side",
  neutral: "Neutral",
};

export const SIDE_COLORS: Record<string, string> = {
  red: "bg-red-600",
  blue: "bg-blue-600",
  neutral: "bg-slate-500",
};

export const SIDE_TEXT_COLORS: Record<string, string> = {
  red: "text-red-400",
  blue: "text-blue-400",
  neutral: "text-slate-400",
};

export const SIDE_BORDER_COLORS: Record<string, string> = {
  red: "border-red-500/40",
  blue: "border-blue-500/40",
  neutral: "border-slate-500/40",
};

export const SIDE_HEX_COLORS: Record<string, string> = {
  red: "#dc2626",
  blue: "#2563eb",
  neutral: "#64748b",
};

export const CATEGORIES = ["military", "political", "humanitarian", "crime", "accident", "other"] as const;
