// Fetch-обёртка для VoiceScreen API.
//
// В dev — все /api/* проксируются Vite на https://voxscreen.ru (см. vite.config.ts).
// В проде — фронт лежит на app.voxscreen.ru, API на voxscreen.ru — указываем абсолютный URL.

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

type RequestOptions = Omit<RequestInit, "body"> & { body?: unknown };

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, headers, ...rest } = options;

  const init: RequestInit = {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(headers ?? {}),
    },
    ...rest,
  };

  if (body !== undefined) {
    init.body = body instanceof FormData ? body : JSON.stringify(body);
    if (body instanceof FormData) {
      // Браузер сам выставит multipart с boundary.
      delete (init.headers as Record<string, string>)["Content-Type"];
    }
  }

  const response = await fetch(`${API_BASE}${path}`, init);

  if (response.status === 204) return undefined as T;

  let payload: unknown;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    throw new ApiError(
      response.status,
      typeof payload === "object" && payload !== null && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : payload,
    );
  }

  return payload as T;
}
