import { useState } from "react";
import { Loader2, UserPlus } from "lucide-react";
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
import { useAuth } from "@/auth/AuthProvider";
import { useTeam } from "@/api/hooks";
import { formatDateTime } from "@/lib/format";
import { InviteTeammateDialog } from "@/components/InviteTeammateDialog";

const ROLE_LABELS: Record<string, string> = {
  client_admin: "Администратор",
  client_user: "Пользователь",
};

export function TeamPage() {
  const { user } = useAuth();
  const { data, isLoading } = useTeam();
  const [inviteOpen, setInviteOpen] = useState(false);

  const canInvite = user?.role === "client_admin";
  const team = data ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Команда</h1>
          <p className="text-sm text-muted-foreground">
            Пользователи, у которых есть доступ к этому кабинету.
          </p>
        </div>
        {canInvite && (
          <Button onClick={() => setInviteOpen(true)}>
            <UserPlus className="h-4 w-4" />
            Пригласить коллегу
          </Button>
        )}
      </div>

      <div className="rounded-lg border bg-card">
        {isLoading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">id</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Роль</TableHead>
                <TableHead>Статус</TableHead>
                <TableHead>Создан</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {team.map((u) => (
                <TableRow key={u.id}>
                  <TableCell className="text-muted-foreground">{u.id}</TableCell>
                  <TableCell className="font-medium">
                    {u.email}
                    {user?.id === u.id && (
                      <span className="ml-2 text-xs text-muted-foreground">(вы)</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {ROLE_LABELS[u.role] ?? u.role}
                  </TableCell>
                  <TableCell>
                    {u.active ? (
                      <Badge variant="success">Активен</Badge>
                    ) : (
                      <Badge variant="secondary">Заблокирован</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(u.created_at)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      <InviteTeammateDialog open={inviteOpen} onOpenChange={setInviteOpen} />
    </div>
  );
}
