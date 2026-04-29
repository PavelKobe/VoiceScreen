import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Loader2, Phone, PhoneCall } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar } from "@/components/Avatar";
import { WaveformPlayer } from "@/components/WaveformPlayer";
import { toast } from "sonner";
import { useCall, useCallCandidate } from "@/api/hooks";
import { ApiError } from "@/lib/api";
import { decisionLabel, decisionVariant, formatDateTime, formatDuration } from "@/lib/format";
import { cn } from "@/lib/utils";

export function CallDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id ? Number(params.id) : null;

  const { data: call, isLoading } = useCall(id);
  const callMutation = useCallCandidate();
  const [retryStatus, setRetryStatus] = useState<"idle" | "queued" | "error">("idle");

  if (isLoading || !call) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const candidate = call.candidate;
  const recordingUrl = call.has_recording ? `/api/v1/calls/${call.id}/recording` : null;

  async function handleRetry() {
    if (!candidate) return;
    try {
      await callMutation.mutateAsync(candidate.id);
      setRetryStatus("queued");
      toast.success("Звонок поставлен в очередь");
    } catch (err) {
      setRetryStatus("error");
      const detail =
        err instanceof ApiError && typeof err.detail === "string"
          ? err.detail
          : "Не удалось поставить в очередь";
      toast.error(detail);
    }
  }

  return (
    <div className="space-y-6">
      <Link
        to={candidate ? `/vacancies/${candidate.vacancy_id}` : "/vacancies"}
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Назад к вакансии
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          {candidate && <Avatar fio={candidate.fio} size="lg" />}
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {candidate ? candidate.fio : `Звонок #${call.id}`}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              {candidate && (
                <span className="inline-flex items-center gap-1">
                  <Phone className="h-3.5 w-3.5" />
                  {candidate.phone}
                </span>
              )}
              <span>{candidate ? "· " : ""}Звонок #{call.id}</span>
              <span>· {formatDateTime(call.started_at)}</span>
              <span>· длительность {formatDuration(call.duration)}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {call.score != null && (
            <div className="rounded-md border bg-card px-3 py-1.5 text-sm">
              score <span className="font-semibold tabular-nums">{call.score.toFixed(1)}</span>
            </div>
          )}
          <Badge variant={decisionVariant(call.decision)}>{decisionLabel(call.decision)}</Badge>
          {candidate && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleRetry()}
              disabled={callMutation.isPending || retryStatus === "queued"}
            >
              {callMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : retryStatus === "queued" ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-600" />
              ) : (
                <PhoneCall className="h-4 w-4" />
              )}
              {retryStatus === "queued" ? "Поставлено в очередь" : "Позвонить ещё раз"}
            </Button>
          )}
        </div>
      </div>

      {recordingUrl && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Запись разговора</CardTitle>
          </CardHeader>
          <CardContent>
            <WaveformPlayer src={recordingUrl} />
          </CardContent>
        </Card>
      )}

      {call.score_reasoning && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Почему такая оценка</CardTitle>
          </CardHeader>
          <CardContent className="text-sm leading-relaxed">{call.score_reasoning}</CardContent>
        </Card>
      )}

      {call.answers && Object.keys(call.answers).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ответы кандидата</CardTitle>
          </CardHeader>
          <CardContent>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2">
              {Object.entries(call.answers).map(([k, v]) => (
                <div key={k} className="flex flex-col">
                  <dt className="text-xs uppercase tracking-wide text-muted-foreground">{k}</dt>
                  <dd className="text-sm">{v}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Транскрипт</CardTitle>
        </CardHeader>
        <CardContent>
          {call.turns.length === 0 ? (
            <p className="text-sm text-muted-foreground">Транскрипт пуст.</p>
          ) : (
            <div className="space-y-3">
              {call.turns.map((t) => (
                <div
                  key={t.order}
                  className={cn(
                    "max-w-[80%] rounded-lg px-3 py-2 text-sm",
                    t.speaker === "agent"
                      ? "bg-muted"
                      : "ml-auto bg-primary/10 text-foreground",
                  )}
                >
                  <div className="mb-0.5 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    {t.speaker === "agent" ? "Агент" : "Кандидат"}
                  </div>
                  <div className="whitespace-pre-wrap">{t.text}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
