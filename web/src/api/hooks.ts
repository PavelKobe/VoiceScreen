import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Call,
  CallDetail,
  CallEnqueued,
  CallsList,
  CandidatesList,
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
      changes: Partial<Pick<Vacancy, "title" | "scenario_name" | "pass_score" | "active">>;
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

export function useCandidates(vacancyId: number | null) {
  return useQuery({
    queryKey: ["candidates", { vacancy_id: vacancyId }],
    enabled: vacancyId !== null,
    queryFn: () => api<CandidatesList>(`/candidates?vacancy_id=${vacancyId}`),
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

// Re-export types for convenience.
export type { Call, CallDetail, Vacancy, VacancyReport };
