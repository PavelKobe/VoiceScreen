import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { Toaster } from "sonner";
import { AuthProvider } from "@/auth/AuthProvider";
import { RequireAuth } from "@/auth/RequireAuth";
import { Layout } from "@/components/Layout";
import { LoginPage } from "@/pages/Login";

// Страницы за RequireAuth грузим лениво — каждая в свой chunk. Браузер
// скачает только то, что нужно для текущего маршрута. Уменьшает первую
// загрузку с ~700 КБ до ~250 КБ и снимает варнинг Vite про chunk > 500 КБ.
const DashboardPage = lazy(() =>
  import("@/pages/Dashboard").then((m) => ({ default: m.DashboardPage })),
);
const VacanciesPage = lazy(() =>
  import("@/pages/Vacancies").then((m) => ({ default: m.VacanciesPage })),
);
const VacancyDetailPage = lazy(() =>
  import("@/pages/VacancyDetail").then((m) => ({ default: m.VacancyDetailPage })),
);
const CallDetailPage = lazy(() =>
  import("@/pages/CallDetail").then((m) => ({ default: m.CallDetailPage })),
);
const CandidateDetailPage = lazy(() =>
  import("@/pages/CandidateDetail").then((m) => ({ default: m.CandidateDetailPage })),
);
const ScenariosPage = lazy(() =>
  import("@/pages/Scenarios").then((m) => ({ default: m.ScenariosPage })),
);
const ScenarioEditPage = lazy(() =>
  import("@/pages/ScenarioEdit").then((m) => ({ default: m.ScenarioEditPage })),
);
const TeamPage = lazy(() =>
  import("@/pages/Team").then((m) => ({ default: m.TeamPage })),
);

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

function PageFallback() {
  return (
    <div className="flex h-64 items-center justify-center">
      <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Toaster position="top-right" richColors closeButton />
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route
                element={
                  <RequireAuth>
                    <Layout />
                  </RequireAuth>
                }
              >
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/vacancies" element={<VacanciesPage />} />
                <Route path="/vacancies/:id" element={<VacancyDetailPage />} />
                <Route path="/calls/:id" element={<CallDetailPage />} />
                <Route path="/candidates/:id" element={<CandidateDetailPage />} />
                <Route path="/scenarios" element={<ScenariosPage />} />
                <Route path="/scenarios/new" element={<ScenarioEditPage />} />
                <Route path="/scenarios/:slug" element={<ScenarioEditPage />} />
                <Route path="/team" element={<TeamPage />} />
              </Route>
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
