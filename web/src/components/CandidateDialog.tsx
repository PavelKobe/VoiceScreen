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
import { useUpdateCandidate } from "@/api/hooks";
import { ApiError } from "@/lib/api";
import type { CandidateRow } from "@/api/types";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  candidate: CandidateRow | null;
}

export function CandidateDialog({ open, onOpenChange, candidate }: Props) {
  const update = useUpdateCandidate();
  const [fio, setFio] = useState("");
  const [phone, setPhone] = useState("");
  const [source, setSource] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && candidate) {
      setFio(candidate.fio);
      setPhone(candidate.phone);
      setSource(candidate.source ?? "");
      setError(null);
    }
  }, [open, candidate]);

  if (!candidate) return null;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!candidate) return;
    setError(null);
    try {
      await update.mutateAsync({
        id: candidate.id,
        changes: { fio, phone, source: source.trim() ? source : null },
      });
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
          <DialogTitle>Изменить кандидата</DialogTitle>
          <DialogDescription>
            Правка ФИО / телефона / источника. История звонков остаётся прежней.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="fio">ФИО</Label>
            <Input
              id="fio"
              value={fio}
              onChange={(e) => setFio(e.target.value)}
              required
              maxLength={255}
              disabled={update.isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">Телефон</Label>
            <Input
              id="phone"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              maxLength={20}
              placeholder="+7XXXXXXXXXX"
              disabled={update.isPending}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="source">Источник</Label>
            <Input
              id="source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              maxLength={50}
              placeholder="hh, avito, referral…"
              disabled={update.isPending}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
            <Button type="submit" disabled={update.isPending}>
              {update.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Сохранить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
