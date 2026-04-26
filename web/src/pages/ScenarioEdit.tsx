import { useEffect, useState, type FormEvent } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { ArrowLeft, Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { QuestionListEditor } from "@/components/QuestionListEditor";
import {
  useCreateScenario,
  useScenario,
  useScenarioTemplate,
  useUpdateScenario,
} from "@/api/hooks";
import { ApiError } from "@/lib/api";
import type { Question, ScenarioCreatePayload } from "@/api/types";

const EMPTY: ScenarioCreatePayload = {
  slug: "",
  title: "",
  agent_role: "HR-помощник",
  company_name: "",
  vacancy_title: "",
  questions: [],
};

export function ScenarioEditPage() {
  const params = useParams<{ slug?: string }>();
  const slug = params.slug ?? null;
  const isEdit = slug !== null;

  const [search] = useSearchParams();
  const templateSlug = search.get("template");

  const navigate = useNavigate();
  const { data: existing, isLoading: loadingExisting } = useScenario(slug);
  const { data: template, isLoading: loadingTemplate } = useScenarioTemplate(
    !isEdit ? templateSlug : null,
  );
  const create = useCreateScenario();
  const update = useUpdateScenario();

  const [draft, setDraft] = useState<ScenarioCreatePayload>(EMPTY);
  const [active, setActive] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isEdit && existing) {
      setDraft({
        slug: existing.slug,
        title: existing.title,
        agent_role: existing.agent_role,
        company_name: existing.company_name,
        vacancy_title: existing.vacancy_title,
        questions: existing.questions,
      });
      setActive(existing.active);
    } else if (!isEdit && template) {
      setDraft({ ...template, slug: "" });
    }
  }, [isEdit, existing, template]);

  const submitting = create.isPending || update.isPending;
  const loading = (isEdit && loadingExisting) || (!isEdit && templateSlug && loadingTemplate);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  function setField<K extends keyof ScenarioCreatePayload>(
    key: K,
    value: ScenarioCreatePayload[K],
  ) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      if (isEdit && slug) {
        await update.mutateAsync({
          slug,
          changes: {
            title: draft.title,
            agent_role: draft.agent_role,
            company_name: draft.company_name,
            vacancy_title: draft.vacancy_title,
            questions: draft.questions,
            active,
          },
        });
        navigate("/scenarios");
      } else {
        const created = await create.mutateAsync(draft);
        navigate(`/scenarios/${created.slug}`);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
      } else {
        setError("Ошибка сети");
      }
    }
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Link
          to="/scenarios"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />К списку сценариев
        </Link>
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold tracking-tight">
            {isEdit ? draft.title || draft.slug : "Новый сценарий"}
          </h1>
          {isEdit && (
            <Badge variant={active ? "success" : "secondary"}>
              {active ? "Активен" : "Архив"}
            </Badge>
          )}
        </div>
      </div>

      <form onSubmit={onSubmit} className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Основное</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="slug">Идентификатор (slug)</Label>
                <Input
                  id="slug"
                  value={draft.slug}
                  onChange={(e) => setField("slug", e.target.value)}
                  required
                  disabled={isEdit || submitting}
                  placeholder="например: cashier_screening"
                />
                <p className="text-xs text-muted-foreground">
                  {isEdit
                    ? "Slug нельзя изменить после создания."
                    : "Латиница, цифры, дефис, подчёркивание (3–100 символов). Используется внутри системы."}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="title">Название (для списка)</Label>
                <Input
                  id="title"
                  value={draft.title}
                  onChange={(e) => setField("title", e.target.value)}
                  required
                  disabled={submitting}
                  placeholder="например: Скрининг продавца-кассира"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="company_name">Название компании</Label>
                <Input
                  id="company_name"
                  value={draft.company_name}
                  onChange={(e) => setField("company_name", e.target.value)}
                  required
                  disabled={submitting}
                  placeholder="например: Стокманн"
                />
                <p className="text-xs text-muted-foreground">
                  Агент будет представляться от лица этой компании.
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="vacancy_title">Позиция</Label>
                <Input
                  id="vacancy_title"
                  value={draft.vacancy_title}
                  onChange={(e) => setField("vacancy_title", e.target.value)}
                  required
                  disabled={submitting}
                  placeholder="например: Продавец-кассир"
                />
              </div>

              <div className="space-y-2 sm:col-span-2">
                <Label htmlFor="agent_role">Роль агента</Label>
                <Textarea
                  id="agent_role"
                  rows={2}
                  value={draft.agent_role}
                  onChange={(e) => setField("agent_role", e.target.value)}
                  required
                  disabled={submitting}
                  placeholder="например: HR-помощник"
                />
                <p className="text-xs text-muted-foreground">
                  Кем агент представляется в начале разговора (например, «HR-помощник»).
                </p>
              </div>
            </div>

            {isEdit && (
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={active}
                  onChange={(e) => setActive(e.target.checked)}
                  className="h-4 w-4 rounded border-input"
                  disabled={submitting}
                />
                Сценарий активен (можно привязать к новой вакансии)
              </label>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Вопросы анкеты</CardTitle>
          </CardHeader>
          <CardContent>
            <QuestionListEditor
              questions={draft.questions}
              onChange={(qs: Question[]) => setField("questions", qs)}
              disabled={submitting}
            />
          </CardContent>
        </Card>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => navigate("/scenarios")}
            disabled={submitting}
          >
            Отмена
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            {isEdit ? "Сохранить" : "Создать сценарий"}
          </Button>
        </div>
      </form>
    </div>
  );
}
