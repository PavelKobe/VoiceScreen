import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Eye,
  Loader2,
  MoreHorizontal,
  Pencil,
  PhoneCall,
  PowerOff,
} from "lucide-react";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { CandidateDialog } from "@/components/CandidateDialog";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  useArchiveCandidate,
  useCallCandidate,
  useCandidates,
} from "@/api/hooks";
import { ApiError } from "@/lib/api";
import { decisionLabel, decisionVariant, formatDateTime } from "@/lib/format";
import type { CandidateRow } from "@/api/types";

const STATUS_LABELS: Record<string, string> = {
  pending: "В очереди",
  called: "Был обзвон",
  failed: "Ошибка",
};

interface Props {
  vacancyId: number;
}

export function CandidatesTable({ vacancyId }: Props) {
  const [showArchived, setShowArchived] = useState(false);
  const { data, isLoading } = useCandidates(vacancyId, { includeArchived: showArchived });
  const callMutation = useCallCandidate();
  const archive = useArchiveCandidate();

  const [editTarget, setEditTarget] = useState<CandidateRow | null>(null);
  const [archiveTarget, setArchiveTarget] = useState<CandidateRow | null>(null);
  const [pendingCalls, setPendingCalls] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  async function handleCall(candidate: CandidateRow) {
    setError(null);
    setPendingCalls((prev) => new Set(prev).add(candidate.id));
    try {
      await callMutation.mutateAsync(candidate.id);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === "string" ? err.detail : "Не удалось поставить звонок");
      } else {
        setError("Ошибка сети");
      }
    } finally {
      setPendingCalls((prev) => {
        const next = new Set(prev);
        next.delete(candidate.id);
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

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm text-muted-foreground">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-input"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
          />
          Показывать архивных
        </label>
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      {items.length === 0 ? (
        <div className="rounded-md border bg-card p-8 text-center text-sm text-muted-foreground">
          Кандидатов пока нет. Загрузите файл на вкладке «Загрузить кандидатов».
        </div>
      ) : (
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
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((c) => {
                const isCalling = pendingCalls.has(c.id);
                const lastCall = c.last_call;
                return (
                  <TableRow key={c.id} className={c.active ? undefined : "opacity-60"}>
                    <TableCell className="text-muted-foreground">{c.id}</TableCell>
                    <TableCell className="font-medium">
                      <Link to={`/candidates/${c.id}`} className="hover:underline">
                        {c.fio}
                      </Link>
                      {!c.active && (
                        <Badge variant="secondary" className="ml-2">
                          Архив
                        </Badge>
                      )}
                    </TableCell>
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
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" disabled={isCalling}>
                            {isCalling ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <MoreHorizontal className="h-4 w-4" />
                            )}
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <Link to={`/candidates/${c.id}`}>
                              <Eye className="h-4 w-4" />
                              Открыть
                            </Link>
                          </DropdownMenuItem>
                          <DropdownMenuItem onSelect={() => setEditTarget(c)}>
                            <Pencil className="h-4 w-4" />
                            Изменить
                          </DropdownMenuItem>
                          {c.active && (
                            <DropdownMenuItem onSelect={() => void handleCall(c)}>
                              <PhoneCall className="h-4 w-4" />
                              Позвонить
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuSeparator />
                          {c.active ? (
                            <DropdownMenuItem
                              className="text-destructive focus:text-destructive"
                              onSelect={() => setArchiveTarget(c)}
                            >
                              <PowerOff className="h-4 w-4" />
                              Архивировать
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem
                              onSelect={() =>
                                void archive.mutate(c.id) // в архиве при выборе сюда — ничего, restore через detail
                              }
                              disabled
                            >
                              Уже в архиве
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <CandidateDialog
        open={editTarget !== null}
        onOpenChange={(o) => !o && setEditTarget(null)}
        candidate={editTarget}
      />

      <ConfirmDialog
        open={archiveTarget !== null}
        onOpenChange={(o) => !o && setArchiveTarget(null)}
        title={`Архивировать ${archiveTarget?.fio ?? "кандидата"}?`}
        description="Кандидат скроется из списка. История звонков и записи разговоров останутся, при необходимости можно восстановить."
        confirmLabel="Архивировать"
        destructive
        pending={archive.isPending}
        onConfirm={async () => {
          if (!archiveTarget) return;
          await archive.mutateAsync(archiveTarget.id);
          setArchiveTarget(null);
        }}
      />
    </div>
  );
}
