import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Eye,
  Loader2,
  MoreHorizontal,
  Pencil,
  PhoneCall,
  PowerOff,
  Search,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { Avatar } from "@/components/Avatar";
import { CandidateDialog } from "@/components/CandidateDialog";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  useArchiveCandidate,
  useCallCandidate,
  useCandidates,
} from "@/api/hooks";
import { toast } from "sonner";
import { ApiError } from "@/lib/api";
import { decisionLabel, decisionVariant, formatDateTime } from "@/lib/format";
import type { CandidateRow } from "@/api/types";

type BadgeVariant = "secondary" | "outline" | "warning" | "success" | "destructive";

/**
 * Резолвим бейдж статуса с учётом подсостояний:
 * - pending + next_attempt_at → "Запланирован" (синий, видно что задача стоит)
 * - pending без next_attempt_at → "Ждёт запуска" (нейтральный outline)
 * - in_progress / done / exhausted — стандартные цвета.
 */
function resolveStatusBadge(c: CandidateRow): { label: string; variant: BadgeVariant } {
  if (c.status === "pending") {
    return c.next_attempt_at
      ? { label: "Запланирован", variant: "secondary" }
      : { label: "Ждёт запуска", variant: "outline" };
  }
  if (c.status === "in_progress") return { label: "Звоним", variant: "warning" };
  if (c.status === "done") return { label: "Готово", variant: "success" };
  if (c.status === "exhausted") return { label: "Не дозвонились", variant: "destructive" };
  // Старые значения для обратной совместимости с БД.
  if (c.status === "called") return { label: "Был обзвон", variant: "secondary" };
  if (c.status === "failed") return { label: "Ошибка", variant: "destructive" };
  return { label: c.status, variant: "outline" };
}

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
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] =
    useState<"all" | "pending" | "in_progress" | "done" | "exhausted">("all");

  async function handleCall(candidate: CandidateRow) {
    setPendingCalls((prev) => new Set(prev).add(candidate.id));
    try {
      await callMutation.mutateAsync(candidate.id);
      toast.success("Звонок поставлен в очередь");
    } catch (err) {
      const detail =
        err instanceof ApiError && typeof err.detail === "string"
          ? err.detail
          : "Не удалось поставить звонок";
      toast.error(detail);
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

  const allItems = data?.items ?? [];

  // Клиентский поиск/фильтр — ОК для пилота при 100+ кандидатов на вакансии.
  // Если будут тысячи — переедет на серверный.
  const normalizedSearch = search.trim().toLowerCase();
  const items = allItems.filter((c) => {
    if (statusFilter !== "all" && c.status !== statusFilter) return false;
    if (!normalizedSearch) return true;
    const fioMatch = c.fio.toLowerCase().includes(normalizedSearch);
    const phoneMatch = c.phone.toLowerCase().includes(normalizedSearch);
    return fioMatch || phoneMatch;
  });

  // Счётчики для филтр-плашек — по полному списку (без поискового среза),
  // чтобы цифры не прыгали при наборе.
  const counts = {
    all: allItems.length,
    pending: allItems.filter((c) => c.status === "pending").length,
    in_progress: allItems.filter((c) => c.status === "in_progress").length,
    done: allItems.filter((c) => c.status === "done").length,
    exhausted: allItems.filter((c) => c.status === "exhausted").length,
  };
  const filterPills: { key: typeof statusFilter; label: string }[] = [
    { key: "all", label: "Все" },
    { key: "pending", label: "В очереди" },
    { key: "in_progress", label: "Звоним" },
    { key: "done", label: "Готово" },
    { key: "exhausted", label: "Не дозвонились" },
  ];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Поиск по ФИО или телефону"
            className="pl-9 pr-9"
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
              aria-label="Очистить поиск"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
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

      <div className="flex flex-wrap gap-1.5">
        {filterPills.map((p) => {
          const active = statusFilter === p.key;
          const count = counts[p.key];
          return (
            <button
              key={p.key}
              type="button"
              onClick={() => setStatusFilter(p.key)}
              className={
                active
                  ? "rounded-full bg-primary px-3 py-1 text-xs font-medium text-primary-foreground"
                  : "rounded-full border bg-card px-3 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
              }
            >
              {p.label} <span className="tabular-nums opacity-80">· {count}</span>
            </button>
          );
        })}
      </div>

      {items.length === 0 ? (
        <div className="rounded-md border bg-card p-8 text-center text-sm text-muted-foreground">
          {allItems.length === 0
            ? "Кандидатов пока нет. Загрузите файл на вкладке «Загрузить кандидатов»."
            : "По фильтру и поиску никого не нашли. Попробуйте сбросить условия."}
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
                <TableHead className="text-right">Попытки</TableHead>
                <TableHead>Следующий звонок</TableHead>
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
                const badge = resolveStatusBadge(c);
                return (
                  <TableRow key={c.id} className={c.active ? undefined : "opacity-60"}>
                    <TableCell className="text-muted-foreground">{c.id}</TableCell>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Avatar fio={c.fio} size="sm" />
                        <Link to={`/candidates/${c.id}`} className="hover:underline">
                          {c.fio}
                        </Link>
                        {!c.active && (
                          <Badge variant="secondary" className="ml-1">
                            Архив
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="font-mono text-xs">{c.phone}</TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {c.source ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={badge.variant}>{badge.label}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm text-muted-foreground">
                      {c.attempts_count} / 3
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {c.next_attempt_at ? formatDateTime(c.next_attempt_at) : "—"}
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
