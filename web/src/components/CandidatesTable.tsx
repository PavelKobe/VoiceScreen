import { useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, PhoneCall } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useCandidates, useCallCandidate } from "@/api/hooks";
import { ApiError } from "@/lib/api";
import { decisionLabel, decisionVariant, formatDateTime } from "@/lib/format";

const STATUS_LABELS: Record<string, string> = {
  pending: "В очереди",
  called: "Был обзвон",
  failed: "Ошибка",
};

interface Props {
  vacancyId: number;
}

export function CandidatesTable({ vacancyId }: Props) {
  const { data, isLoading } = useCandidates(vacancyId);
  const callMutation = useCallCandidate();
  const [pending, setPending] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  async function handleCall(candidateId: number) {
    setError(null);
    setPending((prev) => new Set(prev).add(candidateId));
    try {
      await callMutation.mutateAsync(candidateId);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === "string" ? err.detail : "Не удалось поставить звонок в очередь");
      } else {
        setError("Ошибка сети");
      }
    } finally {
      setPending((prev) => {
        const next = new Set(prev);
        next.delete(candidateId);
        return next;
      });
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-32 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const items = data?.items ?? [];
  if (items.length === 0) {
    return (
      <div className="rounded-md border bg-card p-8 text-center text-sm text-muted-foreground">
        Кандидатов пока нет. Загрузите файл на вкладке «Загрузить кандидатов».
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {error && <p className="text-sm text-destructive">{error}</p>}
      <div className="rounded-lg border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">id</TableHead>
              <TableHead>ФИО</TableHead>
              <TableHead>Телефон</TableHead>
              <TableHead>Источник</TableHead>
              <TableHead>Статус</TableHead>
              <TableHead>Последний звонок</TableHead>
              <TableHead className="text-right">Score</TableHead>
              <TableHead>Решение</TableHead>
              <TableHead className="w-32" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((c) => {
              const isPending = pending.has(c.id);
              const lastCall = c.last_call;
              return (
                <TableRow key={c.id}>
                  <TableCell className="text-muted-foreground">{c.id}</TableCell>
                  <TableCell className="font-medium">{c.fio}</TableCell>
                  <TableCell className="font-mono text-xs">{c.phone}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {c.source ?? "—"}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {STATUS_LABELS[c.status] ?? c.status}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {lastCall ? (
                      <Link to={`/calls/${lastCall.id}`} className="hover:underline">
                        {formatDateTime(lastCall.started_at)}
                      </Link>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell className="text-right tabular-nums">
                    {lastCall?.score != null ? lastCall.score.toFixed(1) : "—"}
                  </TableCell>
                  <TableCell>
                    {lastCall ? (
                      <Badge variant={decisionVariant(lastCall.decision)}>
                        {decisionLabel(lastCall.decision)}
                      </Badge>
                    ) : (
                      "—"
                    )}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void handleCall(c.id)}
                      disabled={isPending}
                    >
                      {isPending ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <PhoneCall className="h-3.5 w-3.5" />
                      )}
                      Позвонить
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
