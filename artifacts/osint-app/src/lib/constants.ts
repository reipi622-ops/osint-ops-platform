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

// ── Side (Red / Blue / Neutral) ────────────────────────────────────────────────
export const SIDE_LABELS: Record<string, string> = {
  red:     "عدو",     // Adversary / Red Force
  blue:    "צה\"ל",  // IDF / Blue Force
  neutral: "ניטרלי",  // Neutral
};

export const SIDE_LABELS_EN: Record<string, string> = {
  red:     "Adversary",
  blue:    "IDF / Blue",
  neutral: "Neutral",
};

export const SIDE_COLORS: Record<string, string> = {
  red:     "bg-red-600",
  blue:    "bg-blue-600",
  neutral: "bg-slate-500",
};

export const SIDE_TEXT_COLORS: Record<string, string> = {
  red:     "text-red-400",
  blue:    "text-blue-400",
  neutral: "text-slate-400",
};

export const SIDE_BORDER_COLORS: Record<string, string> = {
  red:     "border-red-500/40",
  blue:    "border-blue-500/40",
  neutral: "border-slate-500/40",
};

export const SIDE_HEX_COLORS: Record<string, string> = {
  red:     "#dc2626",
  blue:    "#2563eb",
  neutral: "#64748b",
};

// Recharts-compatible fill colors
export const SIDE_CHART_COLORS: Record<string, string> = {
  red:     "#dc2626",
  blue:    "#2563eb",
  neutral: "#64748b",
};

export const CATEGORIES = [
  "military", "political", "humanitarian", "crime", "accident", "other",
] as const;

// ── Importance tag display metadata ───────────────────────────────────────────
// ── Intelligence Confidence Levels ─────────────────────────────────────────────
export const CONFIDENCE_LEVEL_LABELS: Record<string, string> = {
  low:      "Low",
  medium:   "Medium",
  high:     "High",
  verified: "Verified",
};

export const CONFIDENCE_LEVEL_COLORS: Record<string, string> = {
  low:      "bg-slate-500",
  medium:   "bg-yellow-500",
  high:     "bg-emerald-500",
  verified: "bg-violet-500",
};

export const CONFIDENCE_LEVEL_TEXT_COLORS: Record<string, string> = {
  low:      "text-slate-400",
  medium:   "text-yellow-400",
  high:     "text-emerald-400",
  verified: "text-violet-400",
};

export const CONFIDENCE_LEVEL_HEX: Record<string, string> = {
  low:      "#64748b",
  medium:   "#eab308",
  high:     "#10b981",
  verified: "#8b5cf6",
};

export const IMPORTANCE_TAG_LABELS: Record<string, { label: string; icon: string }> = {
  rockets:           { label: "טילים/רקטות",       icon: "🚀" },
  uav:               { label: 'כטב"מ',              icon: "🛸" },
  airstrike:         { label: "תקיפה אווירית",      icon: "✈️" },
  casualties:        { label: "נפגעים",             icon: "🩸" },
  explosion:         { label: "פיצוץ",              icon: "💥" },
  heavy_bombardment: { label: "הפגזה כבדה",         icon: "💣" },
  idf_statement:     { label: 'הודעת צה"ל',         icon: "📢" },
  hezbollah:         { label: "חיזבאללה",           icon: "⚠️" },
  warning_alert:     { label: "אזעקה",              icon: "🚨" },
};
