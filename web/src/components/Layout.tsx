import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { Briefcase, LogOut, Mic2, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/auth/AuthProvider";
import { cn } from "@/lib/utils";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
}

const NAV: NavItem[] = [{ to: "/vacancies", label: "Вакансии", icon: Briefcase }];

export function Layout() {
  const { user, client, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-muted/30">
      <aside className="flex w-60 flex-col border-r bg-card">
        <div className="flex h-16 items-center gap-2 border-b px-6">
          <Mic2 className="h-5 w-5 text-primary" />
          <Link to="/" className="text-lg font-semibold">
            VoiceScreen
          </Link>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t p-3">
          <div className="mb-3 px-2 text-xs text-muted-foreground">
            <div className="truncate font-medium text-foreground">{user?.email}</div>
            <div className="truncate">{client?.name}</div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="w-full justify-start"
            onClick={() => void handleLogout()}
          >
            <LogOut className="h-4 w-4" />
            Выйти
          </Button>
        </div>
      </aside>

      <main className="flex-1 overflow-x-auto">
        <div className="mx-auto max-w-6xl p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
