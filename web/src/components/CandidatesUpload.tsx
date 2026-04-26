import { useCallback, useRef, useState, type ChangeEvent, type DragEvent } from "react";
import { CheckCircle2, FileSpreadsheet, Loader2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useUploadCandidates } from "@/api/hooks";
import { ApiError } from "@/lib/api";
import type { UploadResult } from "@/api/types";
import { cn } from "@/lib/utils";

interface Props {
  vacancyId: number;
}

export function CandidatesUpload({ vacancyId }: Props) {
  const upload = useUploadCandidates();
  const [file, setFile] = useState<File | null>(null);
  const [start, setStart] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = useCallback(async () => {
    if (!file) return;
    setError(null);
    setResult(null);
    try {
      const r = await upload.mutateAsync({ vacancy_id: vacancyId, file, start });
      setResult(r);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
      } else {
        setError("Ошибка загрузки");
      }
    }
  }, [file, start, upload, vacancyId]);

  function onDrop(e: DragEvent<HTMLLabelElement>) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  }

  function onPick(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Загрузить кандидатов</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            className={cn(
              "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-md border-2 border-dashed p-8 transition-colors",
              dragOver ? "border-primary bg-primary/5" : "border-input hover:bg-muted/50",
            )}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".csv,.xlsx"
              className="sr-only"
              onChange={onPick}
            />
            {file ? (
              <>
                <FileSpreadsheet className="h-8 w-8 text-primary" />
                <div className="text-center">
                  <div className="text-sm font-medium">{file.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {(file.size / 1024).toFixed(1)} КБ
                  </div>
                </div>
              </>
            ) : (
              <>
                <Upload className="h-8 w-8 text-muted-foreground" />
                <div className="text-center text-sm text-muted-foreground">
                  Перетащи CSV/XLSX или нажми, чтобы выбрать
                </div>
                <div className="text-xs text-muted-foreground">
                  Колонки: phone, fio, source (опционально)
                </div>
              </>
            )}
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={start}
              onChange={(e) => setStart(e.target.checked)}
              className="h-4 w-4 rounded border-input"
            />
            Сразу запустить обзвон
          </label>

          <div className="flex gap-2">
            <Button onClick={() => void handleSubmit()} disabled={!file || upload.isPending}>
              {upload.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Загрузить
            </Button>
            {file && (
              <Button
                variant="outline"
                onClick={() => {
                  setFile(null);
                  setResult(null);
                  setError(null);
                  if (inputRef.current) inputRef.current.value = "";
                }}
              >
                Очистить
              </Button>
            )}
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          {result && (
            <div className="rounded-md border bg-muted/40 p-4">
              <div className="mb-2 flex items-center gap-2 text-sm font-medium text-emerald-700">
                <CheckCircle2 className="h-4 w-4" />
                Загрузка завершена
              </div>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
                <Stat label="Создано" value={result.created} />
                <Stat label="Дубли" value={result.duplicates} />
                <Stat label="Ошибки" value={result.invalid.length} />
                <Stat label="В очередь" value={result.enqueued} />
              </dl>
              {result.invalid.length > 0 && (
                <details className="mt-3 text-xs">
                  <summary className="cursor-pointer text-muted-foreground">
                    Показать ошибки ({result.invalid.length})
                  </summary>
                  <ul className="mt-2 space-y-1">
                    {result.invalid.map((it, i) => (
                      <li key={i} className="font-mono text-destructive">
                        строка {it.row}: {it.reason}
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-base font-semibold">{value}</dd>
    </div>
  );
}
