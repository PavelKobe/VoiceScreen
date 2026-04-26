import { GripVertical, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { Question, QuestionType } from "@/api/types";

const TYPE_LABEL: Record<QuestionType, string> = {
  open: "Открытый",
  confirm: "Да / Нет",
  choice: "Выбор",
};

interface Props {
  questions: Question[];
  onChange: (qs: Question[]) => void;
  disabled?: boolean;
}

export function QuestionListEditor({ questions, onChange, disabled }: Props) {
  function update(i: number, patch: Partial<Question>) {
    const next = questions.map((q, idx) => (idx === i ? { ...q, ...patch } : q));
    onChange(next);
  }

  function remove(i: number) {
    onChange(questions.filter((_, idx) => idx !== i));
  }

  function add() {
    onChange([...questions, { text: "", type: "open" }]);
  }

  function move(i: number, dir: -1 | 1) {
    const j = i + dir;
    if (j < 0 || j >= questions.length) return;
    const next = [...questions];
    [next[i], next[j]] = [next[j], next[i]];
    onChange(next);
  }

  return (
    <div className="space-y-3">
      {questions.length === 0 && (
        <div className="rounded-md border border-dashed p-6 text-center text-sm text-muted-foreground">
          В сценарии пока нет ни одного вопроса. Добавьте первый.
        </div>
      )}

      {questions.map((q, i) => (
        <div key={i} className="rounded-md border bg-card p-4">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-medium">
              <span className="text-muted-foreground">#{i + 1}</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => move(i, -1)}
                disabled={disabled || i === 0}
                title="Поднять выше"
              >
                <GripVertical className="h-4 w-4 rotate-180" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => move(i, 1)}
                disabled={disabled || i === questions.length - 1}
                title="Опустить ниже"
              >
                <GripVertical className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => remove(i)}
                disabled={disabled}
                title="Удалить"
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1.5 sm:col-span-2">
              <Label className="text-xs">Текст вопроса</Label>
              <Textarea
                value={q.text}
                onChange={(e) => update(i, { text: e.target.value })}
                disabled={disabled}
                rows={2}
                placeholder="Например: Есть ли опыт работы курьером?"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Тип ответа</Label>
              <select
                value={q.type}
                onChange={(e) =>
                  update(i, {
                    type: e.target.value as QuestionType,
                    options: e.target.value === "choice" ? q.options ?? [""] : undefined,
                  })
                }
                disabled={disabled}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {(Object.keys(TYPE_LABEL) as QuestionType[]).map((t) => (
                  <option key={t} value={t}>
                    {TYPE_LABEL[t]}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {q.type === "choice" && (
            <div className="mt-3 space-y-2">
              <Label className="text-xs">Варианты ответа</Label>
              {(q.options ?? []).map((opt, k) => (
                <div key={k} className="flex gap-2">
                  <Input
                    value={opt}
                    onChange={(e) => {
                      const opts = [...(q.options ?? [])];
                      opts[k] = e.target.value;
                      update(i, { options: opts });
                    }}
                    placeholder={`Вариант ${k + 1}`}
                    disabled={disabled}
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      const opts = (q.options ?? []).filter((_, idx) => idx !== k);
                      update(i, { options: opts });
                    }}
                    disabled={disabled}
                  >
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
              ))}
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => update(i, { options: [...(q.options ?? []), ""] })}
                disabled={disabled}
              >
                <Plus className="h-4 w-4" />
                Добавить вариант
              </Button>
            </div>
          )}
        </div>
      ))}

      <Button type="button" variant="outline" onClick={add} disabled={disabled}>
        <Plus className="h-4 w-4" />
        Добавить вопрос
      </Button>
    </div>
  );
}
