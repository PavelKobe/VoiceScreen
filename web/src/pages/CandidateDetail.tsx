import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArchiveRestore,
  Loader2,
  Pencil,
  PhoneCall,
  PowerOff,
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
import { CandidateDialog } from "@/components/CandidateDialog";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  useArchiveCandidate,
  useCallCandidate,
  useCandidate,
  useUpdateCandidate,
} from "@/api/hooks";
import { ApiError } from "@/lib/api";
import { decisionLabel, decisionVariant, formatDateTime, formatDuration } from "@/lib/format";
import type { CandidateRow } from "@/api/types";

export function CandidateDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id ? Number(params.id) : null;

  const { data, isLoading } = useCandidate(id);
  const callMutation = useCallCandidate();
  const archive = useArchiveCandidate();
  const update = useUpdateCandidate();

  const [editOpen, setEditOpen] = useState(false);
  const [archiveOpen, setArchiveOpen] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  if (isLoading || !data) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  async function handleCall() {
    setFeedback(null);
    try {
      await callMutation.mutateAsync(data!.id);
      setFeedback("Звонок поставлен в очередь");
    } catch (err) {
      if (err instanceof ApiError) {
        setFeedback(typeof err.detail === "string" ? err.detail : "Не удалось поставить");
      } else {
        setFeedback("Ошибка сети");
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
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{data.fio}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
            <span className="font-mono">{data.phone}</span>
            {data.source && <span>· источник: {data.source}</span>}
            <span>· добавлен {formatDateTime(data.created_at)}</span>
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

      {feedback && <p className="text-sm text-muted-foreground">{feedback}</p>}

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
    </div>
  );
}
