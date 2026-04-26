import { LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/auth/AuthProvider";

export function HomePage() {
  const { user, client, logout } = useAuth();

  return (
    <div className="min-h-screen bg-muted/40 p-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">VoiceScreen</h1>
          <Button variant="outline" size="sm" onClick={() => void logout()}>
            <LogOut className="h-4 w-4" />
            Выйти
          </Button>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Добро пожаловать, {user?.email}</CardTitle>
            <CardDescription>
              Клиент: {client?.name} (id={client?.id}, тариф {client?.tariff})
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Это заготовка кабинета. Список вакансий, загрузка кандидатов и плеер записей появятся
              на следующем этапе.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
