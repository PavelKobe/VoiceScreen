import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Loader2, MoreHorizontal, Pencil, Plus, PowerOff, Power } from "lucide-react";
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
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { VacancyDialog } from "@/components/VacancyDialog";
import { useVacancies, useDeactivateVacancy, useUpdateVacancy } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";
import type { Vacancy } from "@/api/types";

export function VacanciesPage() {
  const { data, isLoading } = useVacancies();
  const deactivate = useDeactivateVacancy();
  const update = useUpdateVacancy();

  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Vacancy | null>(null);

  const vacancies = useMemo(() => data ?? [], [data]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Вакансии</h1>
          <p className="text-sm text-muted-foreground">
            Управление списком вакансий, по которым ведётся обзвон.
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          Новая вакансия
        </Button>
      </div>

      <div className="rounded-lg border bg-card">
        {isLoading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : vacancies.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            Пока нет вакансий. Нажмите «Новая вакансия» чтобы создать.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">id</TableHead>
                <TableHead>Название</TableHead>
                <TableHead>Сценарий</TableHead>
                <TableHead className="text-right">Порог</TableHead>
                <TableHead>Создана</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {vacancies.map((v) => (
                <TableRow key={v.id}>
                  <TableCell className="text-muted-foreground">{v.id}</TableCell>
                  <TableCell className="font-medium">
                    <Link to={`/vacancies/${v.id}`} className="hover:underline">
                      {v.title}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{v.scenario_name}</TableCell>
                  <TableCell className="text-right">{v.pass_score}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(v.created_at)}
                  </TableCell>
                  <TableCell>
                    {v.active ? (
                      <Badge variant="success">Активна</Badge>
                    ) : (
                      <Badge variant="secondary">Архив</Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={() => setEditing(v)}>
                          <Pencil className="h-4 w-4" />
                          Изменить
                        </DropdownMenuItem>
                        {v.active ? (
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onSelect={() => void deactivate.mutate(v.id)}
                          >
                            <PowerOff className="h-4 w-4" />
                            Деактивировать
                          </DropdownMenuItem>
                        ) : (
                          <DropdownMenuItem
                            onSelect={() =>
                              void update.mutate({ id: v.id, changes: { active: true } })
                            }
                          >
                            <Power className="h-4 w-4" />
                            Активировать
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <VacancyDialog open={createOpen} onOpenChange={setCreateOpen} />
      <VacancyDialog
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
        vacancy={editing}
      />
    </div>
  );
}
