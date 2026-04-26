import { Link } from "react-router-dom";
import { Loader2, Volume2 } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { useCalls } from "@/api/hooks";
import { decisionLabel, decisionVariant, formatDateTime, formatDuration } from "@/lib/format";

interface Props {
  vacancyId: number;
}

export function CallsTable({ vacancyId }: Props) {
  const { data, isLoading } = useCalls({ vacancy_id: vacancyId, limit: 100 });

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
        Звонков пока нет. Загрузите кандидатов и запустите обзвон.
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-16">id</TableHead>
            <TableHead>Кандидат</TableHead>
            <TableHead>Телефон</TableHead>
            <TableHead>Начало</TableHead>
            <TableHead className="text-right">Длительность</TableHead>
            <TableHead className="text-right">Score</TableHead>
            <TableHead>Решение</TableHead>
            <TableHead className="w-12" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((c) => (
            <TableRow key={c.id}>
              <TableCell className="text-muted-foreground">{c.id}</TableCell>
              <TableCell className="font-medium">
                <Link to={`/calls/${c.id}`} className="hover:underline">
                  {c.candidate?.fio ?? "—"}
                </Link>
              </TableCell>
              <TableCell className="font-mono text-xs">{c.candidate?.phone ?? "—"}</TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDateTime(c.started_at)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {formatDuration(c.duration)}
              </TableCell>
              <TableCell className="text-right tabular-nums">
                {c.score != null ? c.score.toFixed(1) : "—"}
              </TableCell>
              <TableCell>
                <Badge variant={decisionVariant(c.decision)}>{decisionLabel(c.decision)}</Badge>
              </TableCell>
              <TableCell>
                {c.has_recording && <Volume2 className="h-4 w-4 text-muted-foreground" />}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
