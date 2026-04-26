import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/auth/AuthProvider";
import { RequireAuth } from "@/auth/RequireAuth";
import { Layout } from "@/components/Layout";
import { LoginPage } from "@/pages/Login";
import { VacanciesPage } from "@/pages/Vacancies";
import { VacancyDetailPage } from "@/pages/VacancyDetail";
import { CallDetailPage } from "@/pages/CallDetail";
import { TeamPage } from "@/pages/Team";
import { ScenariosPage } from "@/pages/Scenarios";
import { ScenarioEditPage } from "@/pages/ScenarioEdit";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              element={
                <RequireAuth>
                  <Layout />
                </RequireAuth>
              }
            >
              <Route path="/" element={<Navigate to="/vacancies" replace />} />
              <Route path="/vacancies" element={<VacanciesPage />} />
              <Route path="/vacancies/:id" element={<VacancyDetailPage />} />
              <Route path="/calls/:id" element={<CallDetailPage />} />
              <Route path="/scenarios" element={<ScenariosPage />} />
              <Route path="/scenarios/new" element={<ScenarioEditPage />} />
              <Route path="/scenarios/:slug" element={<ScenarioEditPage />} />
              <Route path="/team" element={<TeamPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
