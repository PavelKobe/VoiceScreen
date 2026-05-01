import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
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
import { useCreateVacancy, useScenarios, useUpdateVacancy } from "@/api/hooks";
import { ApiError } from "@/lib/api";
import type { NotifyOn, Vacancy } from "@/api/types";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vacancy?: Vacancy | null;
}

export function VacancyDialog({ open, onOpenChange, vacancy }: Props) {
  const editing = vacancy != null;
  const create = useCreateVacancy();
  const update = useUpdateVacancy();
  const { data: scenarios, isLoading: scenariosLoading } = useScenarios({ active: true });

  const [title, setTitle] = useState("");
  const [scenarioName, setScenarioName] = useState("");
  const [passScore, setPassScore] = useState(6);
  const [callSlotsRaw, setCallSlotsRaw] = useState("");
  const [notifyEmailsRaw, setNotifyEmailsRaw] = useState("");
  const [notifyOn, setNotifyOn] = useState<NotifyOn>("pass_review");
  const [smsEnabled, setSmsEnabled] = useState(false);
  const [smsLeadMinutes, setSmsLeadMinutes] = useState(15);
  const [smsTemplate, setSmsTemplate] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && vacancy) {
      setTitle(vacancy.title);
      setScenarioName(vacancy.scenario_name);
      setPassScore(vacancy.pass_score);
      setCallSlotsRaw(vacancy.call_slots ? vacancy.call_slots.join(", ") : "");
      setNotifyEmailsRaw(vacancy.notify_emails ? vacancy.notify_emails.join(", ") : "");
      setNotifyOn(vacancy.notify_on);
      setSmsEnabled(vacancy.sms_enabled);
      setSmsLeadMinutes(vacancy.sms_lead_minutes);
      setSmsTemplate(vacancy.sms_template ?? "");
    } else if (open && !vacancy) {
      setTitle("");
      setScenarioName(scenarios?.[0]?.slug ?? "");
      setPassScore(6);
      setCallSlotsRaw("");
      setNotifyEmailsRaw("");
      setNotifyOn("pass_review");
      setSmsEnabled(false);
      setSmsLeadMinutes(15);
      setSmsTemplate("");
    }
    if (open) setError(null);
  }, [open, vacancy, scenarios]);

  function parseEmails(raw: string): string[] | null {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    return trimmed
      .split(/[,;\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
  }

  /** Парсит строку "10:00, 11:00, 14:00" в массив; пусто → null. */
  function parseSlots(raw: string): string[] | null {
    const trimmed = raw.trim();
    if (!trimmed) return null;
    const parts = trimmed
      .split(/[,\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    return parts;
  }

  const submitting = create.isPending || update.isPending;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const slots = parseSlots(callSlotsRaw);
      const emails = parseEmails(notifyEmailsRaw);
      if (editing && vacancy) {
        await update.mutateAsync({
          id: vacancy.id,
          changes: {
            title,
            pass_score: passScore,
            call_slots: slots,
            notify_emails: emails,
            notify_on: notifyOn,
            sms_enabled: smsEnabled,
            sms_lead_minutes: smsLeadMinutes,
            sms_template: smsTemplate.trim() ? smsTemplate.trim() : null,
          },
        });
      } else {
        await create.mutateAsync({
          title,
          scenario_name: scenarioName,
          pass_score: passScore,
          call_slots: slots,
        });
        // notify/sms-поля для свежей вакансии редактируются после создания
        // через PATCH — на форме создания не загромождаем.
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
            {editing ? (
              <Input id="scenario" value={scenarioName} disabled className="font-mono" />
            ) : scenariosLoading ? (
              <div className="flex h-10 items-center gap-2 rounded-md border bg-muted/40 px-3 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                Загружаем список…
              </div>
            ) : !scenarios || scenarios.length === 0 ? (
              <div className="rounded-md border border-dashed bg-muted/40 p-3 text-sm">
                Сценариев пока нет.{" "}
                <Link
                  to="/scenarios"
                  className="text-primary underline-offset-2 hover:underline"
                  onClick={() => onOpenChange(false)}
                >
                  Создайте первый
                </Link>{" "}
                на странице «Сценарии».
              </div>
            ) : (
              <select
                id="scenario"
                value={scenarioName}
                onChange={(e) => setScenarioName(e.target.value)}
                required
                disabled={submitting}
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {scenarios.map((s) => (
                  <option key={s.slug} value={s.slug}>
                    {s.title} ({s.slug})
                  </option>
                ))}
              </select>
            )}
            {editing && (
              <p className="text-xs text-muted-foreground">
                Сменить сценарий у существующей вакансии можно в БД — но мы стараемся не делать это, чтобы не смешивать звонки разных сценариев в отчёте.
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

          <div className="space-y-2">
            <Label htmlFor="call-slots">График обзвона (необязательно)</Label>
            <Input
              id="call-slots"
              value={callSlotsRaw}
              onChange={(e) => setCallSlotsRaw(e.target.value)}
              placeholder="10:00, 11:00, 14:00"
              disabled={submitting}
              className="font-mono"
            />
            <p className="text-xs text-muted-foreground">
              Время попыток в МСК через запятую: 1-я попытка → первый слот, 2-я → второй и т.д.
              Количество слотов = максимум попыток для этой вакансии.
              Если оставить пустым — действуют общие правила (9:00–21:00, до 3 попыток
              с паузой 30 мин и 2 ч между ними).
            </p>
          </div>

          {editing && (
            <>
              <div className="space-y-2 border-t pt-4">
                <Label htmlFor="notify-emails">Email-уведомления HR</Label>
                <Input
                  id="notify-emails"
                  value={notifyEmailsRaw}
                  onChange={(e) => setNotifyEmailsRaw(e.target.value)}
                  placeholder="hr@company.ru, lead@company.ru"
                  disabled={submitting}
                />
                <select
                  value={notifyOn}
                  onChange={(e) => setNotifyOn(e.target.value as NotifyOn)}
                  disabled={submitting}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <option value="off">Не отправлять</option>
                  <option value="pass_only">Только подходящие (pass)</option>
                  <option value="pass_review">Подходящие и спорные (по умолч.)</option>
                  <option value="all">По всем звонкам</option>
                </select>
                <p className="text-xs text-muted-foreground">
                  Письмо приходит после скоринга, со ссылкой на карточку и записью.
                </p>
              </div>

              {/* SMS-блок скрыт до выбора провайдера (Voximplant sender ID
                  или sms.ru). Бэкенд готов — достаточно вернуть JSX. */}
            </>
          )}

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
