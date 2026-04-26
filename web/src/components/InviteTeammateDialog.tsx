import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Copy, Loader2 } from "lucide-react";
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
import { useInviteTeammate } from "@/api/hooks";
import { ApiError } from "@/lib/api";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function generatePassword(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789";
  let pw = "";
  const arr = new Uint32Array(12);
  crypto.getRandomValues(arr);
  for (const n of arr) pw += alphabet[n % alphabet.length];
  return pw;
}

export function InviteTeammateDialog({ open, onOpenChange }: Props) {
  const invite = useInviteTeammate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [createdEmail, setCreatedEmail] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (open) {
      setEmail("");
      setPassword(generatePassword());
      setError(null);
      setCreatedEmail(null);
      setCopied(false);
    }
  }, [open]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const result = await invite.mutateAsync({ email, password });
      setCreatedEmail(result.email);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(typeof err.detail === "string" ? err.detail : "Не удалось пригласить");
      } else {
        setError("Ошибка сети");
      }
    }
  }

  async function copyCredentials() {
    const text = `Email: ${createdEmail}\nПароль: ${password}\nВход: https://app.voxscreen.ru/login`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Не удалось скопировать");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        {createdEmail ? (
          <>
            <DialogHeader>
              <DialogTitle>Пользователь добавлен</DialogTitle>
              <DialogDescription>
                Скопируйте данные и передайте коллеге защищённым каналом — пароль больше не показывается.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-3 rounded-md border bg-muted/40 p-4">
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Email</div>
                <div className="font-mono text-sm">{createdEmail}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Пароль</div>
                <div className="font-mono text-sm">{password}</div>
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-muted-foreground">Адрес входа</div>
                <div className="font-mono text-sm">https://app.voxscreen.ru/login</div>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => void copyCredentials()}>
                {copied ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
                {copied ? "Скопировано" : "Скопировать"}
              </Button>
              <Button onClick={() => onOpenChange(false)}>Готово</Button>
            </DialogFooter>
          </>
        ) : (
          <form onSubmit={onSubmit}>
            <DialogHeader>
              <DialogTitle>Пригласить коллегу</DialogTitle>
              <DialogDescription>
                Создаём учётку с временным паролем. После создания вы получите данные для передачи.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  required
                  autoComplete="off"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={invite.isPending}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="invite-password">Временный пароль</Label>
                <div className="flex gap-2">
                  <Input
                    id="invite-password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={invite.isPending}
                    className="font-mono"
                  />
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setPassword(generatePassword())}
                    disabled={invite.isPending}
                  >
                    Сгенерировать
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Минимум 6 символов. Коллега сможет сменить пароль позже.
                </p>
              </div>

              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Отмена
              </Button>
              <Button type="submit" disabled={invite.isPending}>
                {invite.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Создать учётку
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
