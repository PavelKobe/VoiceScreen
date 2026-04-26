export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  const mm = Math.floor(seconds / 60);
  const ss = String(seconds % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

export function decisionLabel(decision: string | null): string {
  if (!decision) return "—";
  const map: Record<string, string> = {
    pass: "Прошёл",
    review: "Проверить",
    reject: "Отказ",
  };
  return map[decision] ?? decision;
}

export function decisionVariant(
  decision: string | null,
): "success" | "warning" | "destructive" | "outline" {
  switch (decision) {
    case "pass":
      return "success";
    case "review":
      return "warning";
    case "reject":
      return "destructive";
    default:
      return "outline";
  }
}
