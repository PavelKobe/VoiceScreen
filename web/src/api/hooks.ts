import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Call,
  CallDetail,
  CallEnqueued,
  CallsList,
  CandidateDetail,
  CandidateRow,
  CandidatesList,
  CandidateUpdatePayload,
  DispatchResult,
  Scenario,
  ScenarioBrief,
  ScenarioCreatePayload,
  ScenarioTemplate,
  ScenarioUpdatePayload,
  Teammate,
  UploadResult,
  Vacancy,
  VacancyReport,
} from "./types";

// === Vacancies ===

export function useVacancies(params?: { active?: boolean }) {
  const qs = new URLSearchParams();
  if (params?.active !== undefined) qs.set("active", String(params.active));
  const suffix = qs.toString() ? `?${qs}` : "";
  return useQuery({
    queryKey: ["vacancies", params],
    queryFn: () => api<Vacancy[]>(`/vacancies${suffix}`),
  });
}

export function useVacancy(id: number | null) {
  return useQuery({
    queryKey: ["vacancy", id],
    enabled: id !== null,
    queryFn: () => api<Vacancy>(`/vacancies/${id}`),
  });
}

export function useVacancyReport(id: number | null) {
  return useQuery({
    queryKey: ["vacancy-report", id],
    enabled: id !== null,
    queryFn: () => api<VacancyReport>(`/vacancies/${id}/report`),
  });
}

export function useCreateVacancy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { title: string; scenario_name: string; pass_score: number }) =>
      api<Vacancy>("/vacancies", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vacancies"] }),
  });
}

export function useUpdateVacancy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      changes,
    }: {
      id: number;
      changes: Partial<
        Pick<Vacancy, "title" | "scenario_name" | "pass_score" | "active" | "dispatch_paused">
      >;
    }) => api<Vacancy>(`/vacancies/${id}`, { method: "PATCH", body: changes }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["vacancies"] });
      qc.invalidateQueries({ queryKey: ["vacancy", vars.id] });
    },
  });
}

export function useDeactivateVacancy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/vacancies/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["vacancies"] }),
  });
}

export function useDispatchVacancy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<DispatchResult>(`/vacancies/${id}/dispatch`, { method: "POST" }),
    onSuccess: (_, id) => {
      qc.invalidateQueries({ queryKey: ["candidates", { vacancy_id: id }] });
      qc.invalidateQueries({ queryKey: ["calls", { vacancy_id: id }] });
      qc.invalidateQueries({ queryKey: ["vacancy-report", id] });
    },
  });
}

// === Calls ===

export function useCalls(params: { vacancy_id?: number; limit?: number; offset?: number }) {
  const qs = new URLSearchParams();
  if (params.vacancy_id !== undefined) qs.set("vacancy_id", String(params.vacancy_id));
  if (params.limit !== undefined) qs.set("limit", String(params.limit));
  if (params.offset !== undefined) qs.set("offset", String(params.offset));
  const suffix = qs.toString() ? `?${qs}` : "";
  return useQuery({
    queryKey: ["calls", params],
    queryFn: () => api<CallsList>(`/calls${suffix}`),
  });
}

export function useCall(id: number | null) {
  return useQuery({
    queryKey: ["call", id],
    enabled: id !== null,
    queryFn: () => api<CallDetail>(`/calls/${id}`),
  });
}

// === Candidates ===

export function useCandidates(
  vacancyId: number | null,
  options?: { includeArchived?: boolean },
) {
  const includeArchived = options?.includeArchived ?? false;
  return useQuery({
    queryKey: ["candidates", { vacancy_id: vacancyId, includeArchived }],
    enabled: vacancyId !== null,
    queryFn: () => {
      const qs = new URLSearchParams({ vacancy_id: String(vacancyId) });
      if (includeArchived) qs.set("include_archived", "true");
      return api<CandidatesList>(`/candidates?${qs}`);
    },
  });
}

export function useCandidate(id: number | null) {
  return useQuery({
    queryKey: ["candidate", id],
    enabled: id !== null,
    queryFn: () => api<CandidateDetail>(`/candidates/${id}`),
  });
}

export function useUpdateCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, changes }: { id: number; changes: CandidateUpdatePayload }) =>
      api<CandidateRow>(`/candidates/${id}`, { method: "PATCH", body: changes }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["candidates"] });
      qc.invalidateQueries({ queryKey: ["candidate", vars.id] });
    },
  });
}

export function useArchiveCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/candidates/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["candidates"] }),
  });
}

export function useResetCandidateAttempts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (candidateId: number) =>
      api<CandidateRow>(`/candidates/${candidateId}/reset_attempts`, { method: "POST" }),
    onSuccess: (_, candidateId) => {
      qc.invalidateQueries({ queryKey: ["candidates"] });
      qc.invalidateQueries({ queryKey: ["candidate", candidateId] });
    },
  });
}

export function useCallCandidate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (candidateId: number) =>
      api<CallEnqueued>(`/candidates/${candidateId}/call`, { method: "POST" }),
    onSuccess: (_, candidateId) => {
      // Не знаем точный vacancy_id здесь — инвалидируем все кандидатские/звонковые кеши.
      qc.invalidateQueries({ queryKey: ["candidates"] });
      qc.invalidateQueries({ queryKey: ["calls"] });
      qc.invalidateQueries({ queryKey: ["call", candidateId] });
    },
  });
}

export function useUploadCandidates() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ vacancy_id, file, start }: { vacancy_id: number; file: File; start: boolean }) => {
      const fd = new FormData();
      fd.append("file", file);
      const qs = new URLSearchParams({
        vacancy_id: String(vacancy_id),
        start: String(start),
      });
      return api<UploadResult>(`/candidates/upload?${qs}`, { method: "POST", body: fd });
    },
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["calls", { vacancy_id: vars.vacancy_id }] });
      qc.invalidateQueries({ queryKey: ["vacancy-report", vars.vacancy_id] });
    },
  });
}

// === Team ===

export function useTeam() {
  return useQuery({
    queryKey: ["team"],
    queryFn: () => api<Teammate[]>("/team"),
  });
}

export function useInviteTeammate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { email: string; password: string; role?: string }) =>
      api<Teammate>("/team", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["team"] }),
  });
}

// === Scenarios ===

export function useScenarios(params?: { active?: boolean }) {
  const qs = new URLSearchParams();
  if (params?.active !== undefined) qs.set("active", String(params.active));
  const suffix = qs.toString() ? `?${qs}` : "";
  return useQuery({
    queryKey: ["scenarios", params],
    queryFn: () => api<ScenarioBrief[]>(`/scenarios${suffix}`),
  });
}

export function useScenario(slug: string | null) {
  return useQuery({
    queryKey: ["scenario", slug],
    enabled: slug !== null,
    queryFn: () => api<Scenario>(`/scenarios/${slug}`),
  });
}

export function useScenarioTemplates() {
  return useQuery({
    queryKey: ["scenario-templates"],
    queryFn: () => api<ScenarioTemplate[]>("/scenarios/templates"),
  });
}

export function useScenarioTemplate(slug: string | null) {
  return useQuery({
    queryKey: ["scenario-template", slug],
    enabled: slug !== null,
    queryFn: () => api<ScenarioCreatePayload>(`/scenarios/templates/${slug}`),
  });
}

export function useCreateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: ScenarioCreatePayload) =>
      api<Scenario>("/scenarios", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scenarios"] }),
  });
}

export function useUpdateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ slug, changes }: { slug: string; changes: ScenarioUpdatePayload }) =>
      api<Scenario>(`/scenarios/${slug}`, { method: "PATCH", body: changes }),
    onSuccess: (_, vars) => {
      qc.invalidateQueries({ queryKey: ["scenarios"] });
      qc.invalidateQueries({ queryKey: ["scenario", vars.slug] });
    },
  });
}

// Re-export types for convenience.
export type { Call, CallDetail, Vacancy, VacancyReport };
