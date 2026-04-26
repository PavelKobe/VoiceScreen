import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FileText, Loader2, Plus } from "lucide-react";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useScenarios, useScenarioTemplates } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";

export function ScenariosPage() {
  const { data, isLoading } = useScenarios();
  const [pickerOpen, setPickerOpen] = useState(false);

  const items = data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Сценарии скрининга</h1>
          <p className="text-sm text-muted-foreground">
            Чек-листы вопросов для разговора с кандидатами. К каждой вакансии привязывается один сценарий.
          </p>
        </div>
        <Button onClick={() => setPickerOpen(true)}>
          <Plus className="h-4 w-4" />
          Новый сценарий
        </Button>
      </div>

      <div className="rounded-lg border bg-card">
        {isLoading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : items.length === 0 ? (
          <div className="p-8 text-center text-sm text-muted-foreground">
            Сценариев ещё нет. Создайте первый — можно с нуля или из готового шаблона.
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Название</TableHead>
                <TableHead>Slug</TableHead>
                <TableHead>Компания</TableHead>
                <TableHead>Позиция</TableHead>
                <TableHead className="text-right">Вопросов</TableHead>
                <TableHead>Изменён</TableHead>
                <TableHead>Статус</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium">
                    <Link to={`/scenarios/${s.slug}`} className="hover:underline">
                      {s.title}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{s.slug}</TableCell>
                  <TableCell className="text-sm">{s.company_name}</TableCell>
                  <TableCell className="text-sm">{s.vacancy_title}</TableCell>
                  <TableCell className="text-right tabular-nums">{s.questions_count}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(s.updated_at)}
                  </TableCell>
                  <TableCell>
                    {s.active ? (
                      <Badge variant="success">Активен</Badge>
                    ) : (
                      <Badge variant="secondary">Архив</Badge>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <NewScenarioPicker open={pickerOpen} onOpenChange={setPickerOpen} />
    </div>
  );
}

function NewScenarioPicker({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const navigate = useNavigate();
  const { data: templates, isLoading } = useScenarioTemplates();

  function startBlank() {
    onOpenChange(false);
    navigate("/scenarios/new");
  }

  function startFromTemplate(slug: string) {
    onOpenChange(false);
    navigate(`/scenarios/new?template=${slug}`);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Новый сценарий</DialogTitle>
          <DialogDescription>
            Можно начать с пустого сценария или взять готовый шаблон и доработать.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2">
          <button
            type="button"
            onClick={startBlank}
            className="flex w-full items-center gap-3 rounded-md border bg-card p-4 text-left transition-colors hover:bg-muted/50"
          >
            <Plus className="h-5 w-5 text-primary" />
            <div>
              <div className="font-medium">Пустой сценарий</div>
              <div className="text-xs text-muted-foreground">
                Заполните все поля и список вопросов с нуля.
              </div>
            </div>
          </button>

          <div className="text-xs uppercase tracking-wide text-muted-foreground">
            Готовые шаблоны
          </div>

          {isLoading ? (
            <div className="flex h-16 items-center justify-center">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
          ) : !templates || templates.length === 0 ? (
            <div className="rounded-md border border-dashed p-4 text-center text-xs text-muted-foreground">
              В репозитории нет YAML-шаблонов.
            </div>
          ) : (
            templates.map((t) => (
              <button
                key={t.slug}
                type="button"
                onClick={() => startFromTemplate(t.slug)}
                className="flex w-full items-center gap-3 rounded-md border bg-card p-4 text-left transition-colors hover:bg-muted/50"
              >
                <FileText className="h-5 w-5 text-primary" />
                <div className="flex-1">
                  <div className="font-medium">{t.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {t.company_name && <>«{t.company_name}» · </>}
                    {t.questions_count} вопросов · slug <code>{t.slug}</code>
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Отмена
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
