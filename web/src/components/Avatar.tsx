import { cn } from "@/lib/utils";

interface Props {
  fio: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

const SIZE_CLASSES: Record<NonNullable<Props["size"]>, string> = {
  sm: "h-7 w-7 text-xs",
  md: "h-9 w-9 text-sm",
  lg: "h-12 w-12 text-base",
};

// Палитра — стабильный цвет от хеша ФИО, чтобы один и тот же кандидат
// всегда был одного цвета. Цвета приглушённые, чтобы не отвлекать.
const COLORS = [
  "bg-blue-100 text-blue-700",
  "bg-violet-100 text-violet-700",
  "bg-emerald-100 text-emerald-700",
  "bg-amber-100 text-amber-700",
  "bg-rose-100 text-rose-700",
  "bg-cyan-100 text-cyan-700",
  "bg-fuchsia-100 text-fuchsia-700",
  "bg-lime-100 text-lime-700",
];

function getInitials(fio: string): string {
  const parts = fio.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function colorFor(fio: string): string {
  let hash = 0;
  for (let i = 0; i < fio.length; i++) {
    hash = (hash * 31 + fio.charCodeAt(i)) | 0;
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

export function Avatar({ fio, size = "md", className }: Props) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-medium",
        SIZE_CLASSES[size],
        colorFor(fio),
        className,
      )}
      aria-label={fio}
    >
      {getInitials(fio)}
    </span>
  );
}
