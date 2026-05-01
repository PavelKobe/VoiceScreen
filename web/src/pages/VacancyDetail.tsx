import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  CheckCircle2,
  Download,
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
import { Input } from "@/components/ui/input";
import {
  useCandidates,
  useDispatchPreview,
  useDispatchVacancy,
  useUpdateVacancy,
  useVacancy,
  useVacancyReport,
} from "@/api/hooks";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { formatDateTime } from "@/lib/format";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import { decisionLabel, decisionVariant } from "@/lib/format";
import { CallsTable } from "@/components/CallsTable";
import { CandidatesTable } from "@/components/CandidatesTable";
import { CandidatesUpload } from "@/components/CandidatesUpload";

export function VacancyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id ? Number(params.id) : null;

  const { data: vacancy, isLoading } = useVacancy(id);
  const { data: report } = useVacancyReport(id);
  const { data: candidatesData } = useCandidates(id);
  const dispatch = useDispatchVacancy();
  const updateVacancy = useUpdateVacancy();

  const [dispatchOpen, setDispatchOpen] = useState(false);
  const preview = useDispatchPreview(id, dispatchOpen);
  const qc = useQueryClient();

  // Inline-редактор графика обзвона прямо в модалке
  const [editingSlots, setEditingSlots] = useState(false);
  const [slotsRaw, setSlotsRaw] = useState("");
  const [slotsError, setSlotsError] = useState<string | null>(null);
  useEffect(() => {
    if (dispatchOpen && vacancy) {
      setSlotsRaw(vacancy.call_slots ? vacancy.call_slots.join(", ") : "");
      setEditingSlots(false);
      setSlotsError(null);
    }
  }, [dispatchOpen, vacancy]);

  async function saveSlots() {
    if (!vacancy) return;
    setSlotsError(null);
    const trimmed = slotsRaw.trim();
    const parsed: string[] | null = trimmed
      ? trimmed.split(/[,\s]+/).map((s) => s.trim()).filter(Boolean)
      : null;
    try {
      await updateVacancy.mutateAsync({
        id: vacancy.id,
        changes: { call_slots: parsed },
      });
      setEditingSlots(false);
      // Перезагрузим превью с новыми ETA
      await qc.invalidateQueries({ queryKey: ["dispatch-preview", vacancy.id] });
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === "string"
          ? err.detail
          : "Не удалось сохранить график";
      setSlotsError(detail);
    }
  }

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
              {vacancy.call_slots && vacancy.call_slots.length > 0 && (
                <>
                  {" · график "}
                  <span className="font-mono">{vacancy.call_slots.join(", ")}</span>
                </>
              )}
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
            <Button
              variant="outline"
              size="sm"
              asChild
              title="Скачать XLSX со всеми кандидатами и итогами их последнего звонка"
            >
              <a href={`/api/v1/vacancies/${vacancy.id}/export.xlsx`}>
                <Download className="h-4 w-4" />
                Excel
              </a>
            </Button>
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

      <Dialog open={dispatchOpen} onOpenChange={setDispatchOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Запустить обзвон по вакансии?</DialogTitle>
            <DialogDescription>
              Превью на основе текущего времени и расписания вакансии. ETA ретраев
              приблизительные — реальное время зависит от того, когда завершится
              предыдущая попытка.
            </DialogDescription>
          </DialogHeader>

          {preview.isLoading && (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          )}

          {preview.data && (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-3 gap-2 rounded-md border bg-muted/30 p-3">
                <Stat
                  label="В очередь"
                  value={preview.data.candidates_to_dispatch}
                  highlight
                />
                <Stat
                  label="Пропустим"
                  value={preview.data.skipped_already_called}
                />
                <Stat label="В архиве" value={preview.data.skipped_archived} />
              </div>

              <div>
                <div className="mb-1.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Когда пойдут звонки (МСК)
                </div>
                {preview.data.attempt_etas.length === 0 ? (
                  <div className="rounded-md border bg-card p-3 text-muted-foreground">
                    Нет запланированных попыток.
                  </div>
                ) : (
                  <ul className="space-y-1">
                    {preview.data.attempt_etas.map((iso, i) => (
                      <li
                        key={iso + i}
                        className="flex items-baseline justify-between gap-3 rounded-md border bg-card px-3 py-2"
                      >
                        <span className="text-muted-foreground">
                          {i === 0 ? "1-я попытка" : `Ретрай №${i}`}
                        </span>
                        <span className="font-mono">{formatDateTime(iso)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-md border bg-card p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    График обзвона
                  </div>
                  {!editingSlots && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => setEditingSlots(true)}
                      disabled={updateVacancy.isPending}
                    >
                      Изменить
                    </Button>
                  )}
                </div>

                {editingSlots ? (
                  <div className="mt-2 space-y-2">
                    <Input
                      value={slotsRaw}
                      onChange={(e) => setSlotsRaw(e.target.value)}
                      placeholder="10:00, 11:00, 14:00 (или пусто)"
                      className="font-mono"
                      disabled={updateVacancy.isPending}
                    />
                    <p className="text-xs text-muted-foreground">
                      Время попыток в МСК через запятую: 1-я попытка → 1-й слот,
                      2-я → 2-й и т.д. Количество слотов = максимум попыток.
                      Пусто — окно 9:00–21:00 + backoff 30 мин → 2 ч → 6 ч.
                    </p>
                    {slotsError && (
                      <p className="text-xs text-destructive">{slotsError}</p>
                    )}
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => void saveSlots()}
                        disabled={updateVacancy.isPending}
                      >
                        {updateVacancy.isPending && (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        )}
                        Сохранить
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEditingSlots(false);
                          setSlotsRaw(
                            vacancy.call_slots ? vacancy.call_slots.join(", ") : "",
                          );
                          setSlotsError(null);
                        }}
                        disabled={updateVacancy.isPending}
                      >
                        Отмена
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-1 text-sm">
                    {vacancy.call_slots && vacancy.call_slots.length > 0 ? (
                      <span className="font-mono">
                        {vacancy.call_slots.join(", ")}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">
                        Не задан — звоним сразу в окне 9:00–21:00 МСК с backoff 30 мин → 2 ч → 6 ч
                      </span>
                    )}
                  </div>
                )}
              </div>

              {preview.data.candidates_to_dispatch === 0 && (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                  Сейчас никого не поставим в очередь.{" "}
                  {preview.data.skipped_already_called > 0 && (
                    <>
                      {preview.data.skipped_already_called} кандидат(ов) либо уже
                      обзвонены (с финальным результатом), либо уже стоят в
                      запланированной очереди от прошлого нажатия, либо исчерпали
                      попытки.{" "}
                    </>
                  )}
                  Если хочешь срочно — открой карточку конкретного кандидата и
                  нажми «Позвонить» (это сбросит счётчик и позвонит сейчас).
                </div>
              )}
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDispatchOpen(false)}
              disabled={dispatch.isPending}
            >
              Отмена
            </Button>
            <Button
              disabled={
                dispatch.isPending ||
                !preview.data ||
                preview.data.candidates_to_dispatch === 0
              }
              onClick={async () => {
                if (!id) return;
                try {
                  const result = await dispatch.mutateAsync(id);
                  const base = `Поставлено в очередь: ${result.enqueued}. Пропущено: ${result.skipped_already_called}. Архивных: ${result.skipped_archived}.`;
                  const deferred =
                    result.enqueued > 0 && result.deferred_to
                      ? ` Старт обзвона: ${new Date(result.deferred_to).toLocaleString("ru-RU", { timeZone: "Europe/Moscow" })}.`
                      : "";
                  if (result.enqueued > 0) {
                    toast.success("Обзвон запущен", { description: base + deferred });
                  } else {
                    toast.message("Никого не поставили", { description: base });
                  }
                  setDispatchOpen(false);
                } catch (err) {
                  const detail =
                    err instanceof ApiError && typeof err.detail === "string"
                      ? err.detail
                      : "Не удалось запустить обзвон";
                  toast.error("Ошибка", { description: detail });
                }
              }}
            >
              {dispatch.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Запустить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function Stat({
  label,
  value,
  highlight,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div className="text-center">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div
        className={
          highlight
            ? "text-xl font-semibold tabular-nums text-foreground"
            : "text-xl font-semibold tabular-nums text-muted-foreground"
        }
      >
        {value}
      </div>
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
