import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArchiveRestore,
  Loader2,
  Pencil,
  PhoneCall,
  PhoneForwarded,
  PowerOff,
  RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Avatar } from "@/components/Avatar";
import { CandidateDialog } from "@/components/CandidateDialog";
import { CandidateTimeline } from "@/components/CandidateTimeline";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  useArchiveCandidate,
  useCallCandidate,
  useCallCandidateNow,
  useCandidate,
  useResetCandidateAttempts,
  useUpdateCandidate,
} from "@/api/hooks";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import { decisionLabel, decisionVariant, formatDateTime, formatDuration } from "@/lib/format";
import type { CandidateRow } from "@/api/types";

export function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id ? Number(params.id) : null;

  const { data, isLoading } = useCandidate(id);
  const callMutation = useCallCandidate();
  const callNowMutation = useCallCandidateNow();
  const archive = useArchiveCandidate();
  const update = useUpdateCandidate();
  const resetAttempts = useResetCandidateAttempts();

  const [editOpen, setEditOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [resetOpen, setResetOpen] = useState(false);

  if (isLoading || !data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  async function handleCall() {
    try {
      await callMutation.mutateAsync(data!.id);
      toast.success("Звонок поставлен в очередь");
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(typeof err.detail === "string" ? err.detail : "Не удалось поставить");
      } else {
        toast.error("Ошибка сети");
      }
    }
  }

  async function handleCallNow() {
    try {
      await callNowMutation.mutateAsync(data!.id);
      toast.success("Звоним сейчас", {
        description: "Счётчик попыток сброшен, задача ушла worker'у",
      });
    } catch (err) {
      if (err instanceof ApiError) {
        toast.error(typeof err.detail === "string" ? err.detail : "Не удалось");
      } else {
        toast.error("Ошибка сети");
      }
    }
  }

  const candidateRow: CandidateRow = {
    id: data.id,
    vacancy_id: data.vacancy_id,
    fio: data.fio,
    phone: data.phone,
    source: data.source,
    status: data.status,
    active: data.active,
    attempts_count: data.attempts_count,
    next_attempt_at: data.next_attempt_at,
    created_at: data.created_at,
    last_call: null,
  };

  const successfulCalls = data.calls.length;

  return (
    <div className="space-y-6">
      <Link
        to={`/vacancies/${data.vacancy_id}`}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        К вакансии
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <Avatar fio={data.fio} size="lg" />
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{data.fio}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              <span className="font-mono">{data.phone}</span>
              {data.source && <span>· источник: {data.source}</span>}
              <span>· добавлен {formatDateTime(data.created_at)}</span>
            </div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={data.active ? "success" : "secondary"}>
            {data.active ? "Активен" : "Архив"}
          </Badge>
          <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
            <Pencil className="h-4 w-4" />
            Изменить
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void handleCall()}
            disabled={!data.active || callMutation.isPending}
          >
            {callMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <PhoneCall className="h-4 w-4" />
            )}
            Позвонить
          </Button>
          <Button
            size="sm"
            onClick={() => void handleCallNow()}
            disabled={
              !data.active ||
              data.status === "in_progress" ||
              callNowMutation.isPending
            }
            title="Сбросить счётчик попыток и позвонить немедленно (для тестов / ручных перезвонов)"
          >
            {callNowMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <PhoneForwarded className="h-4 w-4" />
            )}
            Позвонить сейчас
          </Button>
          {data.active &&
            data.status !== "in_progress" &&
            (data.attempts_count > 0 || data.next_attempt_at !== null) && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setResetOpen(true)}
                disabled={resetAttempts.isPending}
              >
                {resetAttempts.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <RotateCcw className="h-4 w-4" />
                )}
                {data.attempts_count > 0
                  ? "Сбросить попытки"
                  : "Отменить запланированный"}
              </Button>
            )}
          {data.active ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setArchiveOpen(true)}
              className="text-destructive hover:text-destructive"
            >
              <PowerOff className="h-4 w-4" />
              Архивировать
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                void update.mutate({ id: data.id, changes: { active: true } })
              }
              disabled={update.isPending}
            >
              {update.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArchiveRestore className="h-4 w-4" />
              )}
              Восстановить
            </Button>
          )}
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <CandidateTimeline
            status={data.status}
            attemptsCount={data.attempts_count}
            hasAnyCall={data.calls.length > 0}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">История звонков</CardTitle>
        </CardHeader>
        <CardContent>
          {successfulCalls === 0 ? (
            <p className="text-sm text-muted-foreground">Звонков по этому кандидату пока не было.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">id</TableHead>
                  <TableHead>Начало</TableHead>
                  <TableHead>Завершение</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead>Решение</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.calls.map((c) => {
                  const duration =
                    c.started_at && c.finished_at
                      ? Math.round(
                          (new Date(c.finished_at).getTime() -
                            new Date(c.started_at).getTime()) /
                            1000,
                        )
                      : null;
                  return (
                    <TableRow key={c.id}>
                      <TableCell className="text-muted-foreground">
                        <Link to={`/calls/${c.id}`} className="hover:underline">
                          {c.id}
                        </Link>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDateTime(c.started_at)}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {c.finished_at ? formatDuration(duration) : "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {c.score != null ? c.score.toFixed(1) : "—"}
                      </TableCell>
                      <TableCell>
                        <Badge variant={decisionVariant(c.decision)}>
                          {decisionLabel(c.decision)}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <CandidateDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        candidate={candidateRow}
      />

      <ConfirmDialog
        open={archiveOpen}
        onOpenChange={setArchiveOpen}
        title="Архивировать кандидата?"
        description="Кандидат скроется из списка вакансии. История звонков и записи разговоров останутся. Можно восстановить позже."
        confirmLabel="Архивировать"
        destructive
        pending={archive.isPending}
        onConfirm={async () => {
          await archive.mutateAsync(data.id);
          setArchiveOpen(false);
        }}
      />

      <ConfirmDialog
        open={resetOpen}
        onOpenChange={setResetOpen}
        title={
          data.attempts_count > 0
            ? "Сбросить попытки звонков?"
            : "Отменить запланированный обзвон?"
        }
        description={
          data.attempts_count > 0
            ? "Счётчик попыток обнулится, кандидат снова попадёт в очередь при следующем нажатии «Запустить обзвон». История прошлых звонков и записи сохранятся."
            : "Запланированная задача будет отменена — звонок не уйдёт. Кандидат вернётся в статус «Ждёт запуска». Чтобы возобновить — нажмите «Запустить обзвон» по вакансии."
        }
        confirmLabel={data.attempts_count > 0 ? "Сбросить" : "Отменить звонок"}
        pending={resetAttempts.isPending}
        onConfirm={async () => {
          try {
            const wasScheduled = data.attempts_count === 0 && data.next_attempt_at !== null;
            await resetAttempts.mutateAsync(data.id);
            toast.success(
              wasScheduled ? "Запланированный обзвон отменён" : "Попытки сброшены",
              {
                description: wasScheduled
                  ? "Кандидат вернулся в статус «Ждёт запуска»"
                  : "Кандидат снова в очереди обзвона",
              },
            );
          } catch (err) {
            if (err instanceof ApiError) {
              toast.error(
                typeof err.detail === "string" ? err.detail : "Не удалось сбросить",
              );
            } else {
              toast.error("Ошибка сети");
            }
          }
          setResetOpen(false);
        }}
      />
    </div>
  );
}
