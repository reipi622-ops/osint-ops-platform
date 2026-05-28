import { Badge } from "@/components/ui/badge";
import { ESCALATION_LEVEL_COLORS, ESCALATION_LEVEL_LABELS } from "@/lib/constants";

interface Props {
  level?: string | null;
  className?: string;
}

export function EscalationBadge({ level, className = "" }: Props) {
  const l = level ?? "low";
  const colorClass = ESCALATION_LEVEL_COLORS[l] ?? "bg-slate-500";
  const label = (ESCALATION_LEVEL_LABELS[l] ?? l).toUpperCase();
  const pulse = l === "critical" ? " animate-pulse" : "";

  return (
    <Badge
      className={`font-mono border-none text-white shrink-0 inline-flex items-center gap-0.5 ${colorClass}${pulse} ${className}`}
    >
      {l === "critical" && "⚠ "}
      {label}
    </Badge>
  );
}
