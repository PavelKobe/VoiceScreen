import { Check, CircleDashed, Loader2, PhoneOff, UserPlus } from "lucide-react";
import { cn } from "@/lib/utils";

type Status = "pending" | "in_progress" | "done" | "exhausted" | string;

interface Props {
  status: Status;
  attemptsCount: number;
  hasAnyCall: boolean;
}

interface Step {
  key: string;
  label: string;
  icon: typeof Check;
  active: boolean;
  passed: boolean;
  failed?: boolean;
}

/**
 * Визуальный таймлайн состояний кандидата от момента загрузки до завершения.
 *
 * Логика:
 * - "Загружен" — всегда passed (раз карточка кандидата открыта).
 * - "В очереди" — passed, как только кандидат активен. Active при status=pending.
 * - "Звоним" — active при in_progress, passed при наличии хотя бы одного звонка
 *   или при done/exhausted.
 * - "Готово" — active+passed при done. Failed-вариант с PhoneOff при exhausted.
 */
export function CandidateTimeline({ status, attemptsCount, hasAnyCall }: Props) {
  const isExhausted = status === "exhausted";
  const isDone = status === "done";
  const isInProgress = status === "in_progress";
  const startedAtLeastOnce = hasAnyCall || attemptsCount > 0 || isInProgress || isDone || isExhausted;

  const steps: Step[] = [
    {
      key: "loaded",
      label: "Загружен",
      icon: UserPlus,
      active: false,
      passed: true,
    },
    {
      key: "queued",
      label: "В очереди",
      icon: CircleDashed,
      active: status === "pending" && !startedAtLeastOnce,
      passed: true,
    },
    {
      key: "calling",
      label: "Звоним",
      icon: Loader2,
      active: isInProgress,
      passed: startedAtLeastOnce,
    },
    isExhausted
      ? {
          key: "exhausted",
          label: "Не дозвонились",
          icon: PhoneOff,
          active: true,
          passed: true,
          failed: true,
        }
      : {
          key: "done",
          label: "Готово",
          icon: Check,
          active: isDone,
          passed: isDone,
        },
  ];

  return (
    <div className="flex items-center gap-1 overflow-x-auto py-2">
      {steps.map((step, i) => {
        const Icon = step.icon;
        return (
          <div key={step.key} className="flex items-center gap-1">
            <div className="flex flex-col items-center gap-1">
              <div
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-colors",
                  step.failed
                    ? "border-destructive bg-destructive/10 text-destructive"
                    : step.active
                    ? "border-primary bg-primary/10 text-primary"
                    : step.passed
                    ? "border-emerald-500 bg-emerald-50 text-emerald-600"
                    : "border-muted bg-muted/30 text-muted-foreground",
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4",
                    step.active && step.key === "calling" && "animate-spin",
                  )}
                />
              </div>
              <div
                className={cn(
                  "whitespace-nowrap text-xs",
                  step.failed
                    ? "font-medium text-destructive"
                    : step.active
                    ? "font-medium text-foreground"
                    : step.passed
                    ? "text-foreground"
                    : "text-muted-foreground",
                )}
              >
                {step.label}
              </div>
            </div>
            {i < steps.length - 1 && (
              <div
                className={cn(
                  "mb-5 h-0.5 w-12 transition-colors md:w-20",
                  steps[i + 1].passed ? "bg-emerald-300" : "bg-muted",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
