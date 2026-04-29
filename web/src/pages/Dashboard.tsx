import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Briefcase,
  Loader2,
  PhoneCall,
  TrendingUp,
  Users,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar } from "@/components/Avatar";
import { useDashboard } from "@/api/hooks";
import { decisionLabel, decisionVariant, formatDateTime } from "@/lib/format";

const STATUS_LABELS: Record<string, string> = {
  pending: "В очереди",
  in_progress: "Звоним",
  done: "Готово",
  exhausted: "Не дозвонились",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-blue-100 text-blue-700",
  in_progress: "bg-amber-100 text-amber-700",
  done: "bg-emerald-100 text-emerald-700",
  exhausted: "bg-rose-100 text-rose-700",
};

function formatDayLabel(iso: string): string {
  const d = new Date(iso + "T00:00:00Z");
  return d.toLocaleDateString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    timeZone: "Europe/Moscow",
  });
}

export function DashboardPage() {
  const { data, isLoading } = useDashboard();

  if (isLoading || !data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const chartData = data.calls_by_day.map((d) => ({
    label: formatDayLabel(d.date),
    count: d.count,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Дашборд</h1>
        <p className="text-sm text-muted-foreground">Сводка по обзвону и кандидатам</p>
      </div>

      {/* KPI плитки */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi
          label="Активных вакансий"
          value={data.active_vacancies}
          icon={Briefcase}
          iconClass="bg-blue-50 text-blue-600"
        />
        <Kpi
          label="Кандидатов"
          value={data.candidates_total}
          icon={Users}
          iconClass="bg-violet-50 text-violet-600"
        />
        <Kpi
          label="Звонков сегодня"
          value={data.calls_today}
          subValue={`всего ${data.calls_total}`}
          icon={PhoneCall}
          iconClass="bg-emerald-50 text-emerald-600"
        />
        <Kpi
          label="Средний score"
          value={data.avg_score != null ? data.avg_score.toFixed(2) : "—"}
          icon={TrendingUp}
          iconClass="bg-amber-50 text-amber-600"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* График звонков по дням */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Звонки за 7 дней</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={{ fontSize: 12, fill: "#64748b" }}
                  axisLine={{ stroke: "#cbd5e1" }}
                  tickLine={false}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: 12, fill: "#64748b" }}
                  axisLine={{ stroke: "#cbd5e1" }}
                  tickLine={false}
                  width={28}
                />
                <Tooltip
                  cursor={{ fill: "#f1f5f9" }}
                  contentStyle={{
                    border: "1px solid #e2e8f0",
                    borderRadius: 6,
                    fontSize: 13,
                  }}
                />
                <Bar dataKey="count" fill="#2563eb" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Кандидаты по статусу */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Кандидаты по статусу</CardTitle>
          </CardHeader>
          <CardContent>
            {Object.keys(data.by_status).length === 0 ? (
              <p className="text-sm text-muted-foreground">Кандидатов пока нет.</p>
            ) : (
              <div className="space-y-2">
                {Object.entries(data.by_status).map(([status, count]) => (
                  <div
                    key={status}
                    className="flex items-center justify-between rounded-md border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <span
                        className={
                          "inline-flex h-7 w-7 items-center justify-center rounded-full text-xs font-medium " +
                          (STATUS_COLORS[status] ?? "bg-muted text-muted-foreground")
                        }
                      >
                        {count}
                      </span>
                      <span className="text-sm">
                        {STATUS_LABELS[status] ?? status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Решения по звонкам */}
      {Object.keys(data.by_decision).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Решения по звонкам</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {Object.entries(data.by_decision).map(([d, count]) => (
              <Badge key={d} variant={decisionVariant(d)}>
                {decisionLabel(d)} · {count}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Последние звонки */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Последние звонки</CardTitle>
        </CardHeader>
        <CardContent>
          {data.recent_calls.length === 0 ? (
            <p className="text-sm text-muted-foreground">Звонков пока не было.</p>
          ) : (
            <div className="divide-y">
              {data.recent_calls.map((c) => (
                <Link
                  key={c.id}
                  to={`/calls/${c.id}`}
                  className="flex items-center justify-between gap-3 py-3 transition-colors hover:bg-muted/40 -mx-3 px-3 rounded-md"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Avatar fio={c.candidate_fio} size="sm" />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {c.candidate_fio}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {formatDateTime(c.started_at)}
                      </div>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    {c.score != null && (
                      <span className="font-mono text-sm tabular-nums">
                        {c.score.toFixed(1)}
                      </span>
                    )}
                    <Badge variant={decisionVariant(c.decision)}>
                      {decisionLabel(c.decision)}
                    </Badge>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Kpi({
  label,
  value,
  subValue,
  icon: Icon,
  iconClass,
}: {
  label: string;
  value: number | string;
  subValue?: string;
  icon: LucideIcon;
  iconClass: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${iconClass}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            {label}
          </div>
          <div className="mt-0.5 text-2xl font-semibold tabular-nums">{value}</div>
          {subValue && (
            <div className="text-xs text-muted-foreground">{subValue}</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
