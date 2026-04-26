import { useEffect, useState, type FormEvent } from "react";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { useCreateVacancy, useUpdateVacancy } from "@/api/hooks";
import { ApiError } from "@/lib/api";
import type { Vacancy } from "@/api/types";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vacancy?: Vacancy | null;
}

export function VacancyDialog({ open, onOpenChange, vacancy }: Props) {
  const editing = vacancy != null;
  const create = useCreateVacancy();
  const update = useUpdateVacancy();

  const [title, setTitle] = useState("");
  const [scenarioName, setScenarioName] = useState("courier_screening");
  const [passScore, setPassScore] = useState(6);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && vacancy) {
      setTitle(vacancy.title);
      setScenarioName(vacancy.scenario_name);
      setPassScore(vacancy.pass_score);
    } else if (open && !vacancy) {
      setTitle("");
      setScenarioName("courier_screening");
      setPassScore(6);
    }
    if (open) setError(null);
  }, [open, vacancy]);

  const submitting = create.isPending || update.isPending;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (editing && vacancy) {
        await update.mutateAsync({
          id: vacancy.id,
          changes: { title, pass_score: passScore },
        });
      } else {
        await create.mutateAsync({ title, scenario_name: scenarioName, pass_score: passScore });
      }
      onOpenChange(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
      } else {
        setError("Ошибка сети");
      }
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{editing ? "Изменить вакансию" : "Новая вакансия"}</DialogTitle>
          <DialogDescription>
            {editing
              ? "Можно поменять название и порог прохождения"
              : "Кандидаты загружаются после создания"}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="title">Название</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              maxLength={255}
              disabled={submitting}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="scenario">Сценарий</Label>
            <Input
              id="scenario"
              value={scenarioName}
              onChange={(e) => setScenarioName(e.target.value)}
              required
              disabled={submitting || editing}
            />
            {!editing && (
              <p className="text-xs text-muted-foreground">
                Доступные значения определяются YAML-файлами в <code>scenarios/</code>.
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="pass-score">Порог прохождения (0–10)</Label>
            <Input
              id="pass-score"
              type="number"
              min={0}
              max={10}
              step={0.5}
              value={passScore}
              onChange={(e) => setPassScore(Number(e.target.value))}
              required
              disabled={submitting}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {editing ? "Сохранить" : "Создать"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
