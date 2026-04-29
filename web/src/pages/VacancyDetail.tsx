import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Loader2,
  Pause,
  PauseCircle,
  PhoneCall,
  PhoneOutgoing,
  Play,
  TrendingUp,
  Users,
  type LucideIcon,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import {
  useCandidates,
  useDispatchVacancy,
  useUpdateVacancy,
  useVacancy,
  useVacancyReport,
} from "@/api/hooks";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import { decisionLabel, decisionVariant } from "@/lib/format";
import { CallsTable } from "@/components/CallsTable";
import { CandidatesTable } from "@/components/CandidatesTable";
import { CandidatesUpload } from "@/components/CandidatesUpload";
import { ConfirmDialog } from "@/components/ConfirmDialog";

export function VacancyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id ? Number(params.id) : null;

  const { data: vacancy, isLoading } = useVacancy(id);
  const { data: report } = useVacancyReport(id);
  const { data: candidatesData } = useCandidates(id);
  const dispatch = useDispatchVacancy();
  const updateVacancy = useUpdateVacancy();

  const [dispatchOpen, setDispatchOpen] = useState(false);

  // Кандидаты для bulk — все активные. Бэк сам пропустит финализированных
  // (decision in pass/reject/review), exhausted'ов и тех, кто уже исчерпал
  // попытки. Кандидаты с прошлым "not_reached" попадут на retry.
  const candidates = candidatesData?.items ?? [];
  const dispatchableCount = candidates.filter((c) => c.active).length;

  if (isLoading || !vacancy) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link
          to="/vacancies"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />К списку вакансий
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{vacancy.title}</h1>
            <p className="text-sm text-muted-foreground">
              <span className="font-mono">{vacancy.scenario_name}</span> · порог {vacancy.pass_score}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={vacancy.active ? "success" : "secondary"}>
              {vacancy.active ? "Активна" : "Архив"}
            </Badge>
            {vacancy.active && vacancy.dispatch_paused && (
              <Badge variant="warning">Обзвон на паузе</Badge>
            )}
            {vacancy.active && (
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  void updateVacancy.mutate({
                    id: vacancy.id,
                    changes: { dispatch_paused: !vacancy.dispatch_paused },
                  })
                }
                disabled={updateVacancy.isPending}
                title={
                  vacancy.dispatch_paused
                    ? "Возобновить обзвон по вакансии"
                    : "Приостановить обзвон — стоящие в очереди задачи будут пропущены"
                }
              >
                {updateVacancy.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : vacancy.dispatch_paused ? (
                  <Play className="h-4 w-4" />
                ) : (
                  <Pause className="h-4 w-4" />
                )}
                {vacancy.dispatch_paused ? "Возобновить" : "Приостановить"}
              </Button>
            )}
            {vacancy.active && (
              <Button
                onClick={() => setDispatchOpen(true)}
                disabled={
                  dispatchableCount === 0 ||
                  dispatch.isPending ||
                  vacancy.dispatch_paused
                }
                title={
                  vacancy.dispatch_paused
                    ? "Обзвон приостановлен — снимите паузу"
                    : dispatchableCount === 0
                    ? "Нет необзвонённых кандидатов"
                    : `Поставить в очередь ${dispatchableCount} звонков`
                }
              >
                {dispatch.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <PhoneOutgoing className="h-4 w-4" />
                )}
                Запустить обзвон{dispatchableCount > 0 && ` (${dispatchableCount})`}
              </Button>
            )}
          </div>
        </div>
      </div>

      {vacancy.active && vacancy.dispatch_paused && (
        <div className="flex items-start gap-3 rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          <PauseCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
          <div className="flex-1">
            <div className="font-medium">Обзвон по вакансии приостановлен</div>
            <div className="mt-0.5 text-amber-800/80">
              Уже стоящие в очереди задачи будут пропущены, новые не запускаются.
              Нажмите «Возобновить», чтобы продолжить.
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <ReportCard
          label="Кандидатов"
          value={report?.candidates_total}
          icon={Users}
          iconClassName="bg-blue-50 text-blue-600"
        />
        <ReportCard
          label="Звонков"
          value={report?.calls_total}
          icon={PhoneCall}
          iconClassName="bg-violet-50 text-violet-600"
        />
        <ReportCard
          label="С оценкой"
          value={report?.calls_with_score}
          icon={CheckCircle2}
          iconClassName="bg-emerald-50 text-emerald-600"
        />
        <ReportCard
          label="Средний score"
          value={report?.avg_score != null ? report.avg_score.toFixed(2) : "—"}
          icon={TrendingUp}
          iconClassName="bg-amber-50 text-amber-600"
        />
      </div>

      {report && Object.keys(report.by_decision).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Решения по звонкам</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {Object.entries(report.by_decision).map(([d, count]) => (
              <Badge key={d} variant={decisionVariant(d)}>
                {decisionLabel(d)} · {count}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}

      <Tabs defaultValue="candidates">
        <TabsList>
          <TabsTrigger value="candidates">Кандидаты</TabsTrigger>
          <TabsTrigger value="calls">Звонки</TabsTrigger>
          <TabsTrigger value="upload">Загрузить кандидатов</TabsTrigger>
        </TabsList>
        <TabsContent value="candidates">
          <CandidatesTable vacancyId={vacancy.id} />
        </TabsContent>
        <TabsContent value="calls">
          <CallsTable vacancyId={vacancy.id} />
        </TabsContent>
        <TabsContent value="upload">
          <CandidatesUpload vacancyId={vacancy.id} />
        </TabsContent>
      </Tabs>

      <ConfirmDialog
        open={dispatchOpen}
        onOpenChange={setDispatchOpen}
        title={`Запустить обзвон по ${dispatchableCount} кандидатам?`}
        description="В очередь будут поставлены все активные кандидаты. Бэк автоматически пропустит уже обзвонённых (с финальным результатом) и тех, кто исчерпал попытки. Если сейчас вне окна 9:00–21:00 МСК — звонки уйдут утром."
        confirmLabel="Запустить"
        pending={dispatch.isPending}
        onConfirm={async () => {
          if (!id) return;
          try {
            const result = await dispatch.mutateAsync(id);
            const base = `Поставлено в очередь: ${result.enqueued}. Пропущено: ${result.skipped_already_called}. Архивных: ${result.skipped_archived}.`;
            const deferred = result.enqueued > 0 && result.deferred_to
              ? ` Старт обзвона: ${new Date(result.deferred_to).toLocaleString("ru-RU", { timeZone: "Europe/Moscow" })}.`
              : "";
            if (result.enqueued > 0) {
              toast.success("Обзвон запущен", { description: base + deferred });
            } else {
              toast.message("Никого не поставили", { description: base });
            }
            setDispatchOpen(false);
          } catch (err) {
            const detail = err instanceof ApiError && typeof err.detail === "string"
              ? err.detail
              : "Не удалось запустить обзвон";
            toast.error("Ошибка", { description: detail });
          }
        }}
      />
    </div>
  );
}

function ReportCard({
  label,
  value,
  icon: Icon,
  iconClassName,
}: {
  label: string;
  value: number | string | undefined;
  icon: LucideIcon;
  iconClassName?: string;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-3 p-4">
        <div
          className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted ${iconClassName ?? "text-muted-foreground"}`}
        >
          <Icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
          <div className="mt-0.5 text-2xl font-semibold tabular-nums">
            {value ?? <span className="text-muted-foreground">—</span>}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
