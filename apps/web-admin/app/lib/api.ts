import { dashboardMetrics, fallbackLandmarks } from "@aether/design-system/demo-data";

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window === "object") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
}

type ApiEnvelope<T> = {
  data: T;
  code: string;
  message: string;
  trace_id: string;
};

export type DashboardOverview = {
  active_sessions: number;
  token_cost_usd_today: number;
  cache_hit_rate: number;
  nps: number;
};

export class ApiError extends Error {
  readonly code: string;
  readonly status: number;
  readonly trace_id: string;

  constructor(message: string, code: string, status: number, trace_id: string) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.trace_id = trace_id;
  }
}

// --- Token store ------------------------------------------------------------

const ADMIN_KEY = "aether.admin.token";
const TOURIST_KEY = "aether.admin.tourist.token";

function read(key: string): string | null {
  if (typeof window !== "object") return null;
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  if (typeof window !== "object") return;
  try {
    window.sessionStorage.setItem(key, value);
  } catch {
    // Safari private mode / sandboxed iframe — silently degrade.
  }
}

function clear(key: string): void {
  if (typeof window !== "object") return;
  try {
    window.sessionStorage.removeItem(key);
  } catch {
    // ignored
  }
}

export function getAdminToken(): string | null {
  return read(ADMIN_KEY);
}

export function clearAdminToken(): void {
  clear(ADMIN_KEY);
  clear(TOURIST_KEY);
}

function redirectToLogin(): void {
  if (typeof window !== "object") return;
  clearAdminToken();
  if (window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

let touristBootstrap: Promise<string> | null = null;
async function ensureTouristToken(forceRefresh = false): Promise<string> {
  if (!forceRefresh) {
    const cached = read(TOURIST_KEY);
    if (cached) return cached;
  } else {
    clear(TOURIST_KEY);
  }
  if (touristBootstrap) return touristBootstrap;
  touristBootstrap = (async () => {
    const response = await fetch(`${getApiBase()}/api/v1/auth/anonymous`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}"
    });
    const payload = (await response.json()) as ApiEnvelope<{ token: string }>;
    const token = payload.data?.token ?? "";
    if (token) write(TOURIST_KEY, token);
    touristBootstrap = null;
    return token;
  })();
  return touristBootstrap;
}

// --- Trace ------------------------------------------------------------------

function randomTraceId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID().replace(/-/g, "");
  }
  return Math.random().toString(16).slice(2).padEnd(16, "0");
}

let lastTraceId = "";
export function getLastTraceId(): string {
  return lastTraceId;
}

// --- Request helper ---------------------------------------------------------

type Attempt<T> = { response: Response; payload: ApiEnvelope<T> | null };

async function doFetch<T>(
  path: string,
  init: RequestInit | undefined,
  token: string | null,
  traceId: string
): Promise<Attempt<T>> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Trace-Id": traceId
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  Object.assign(headers, (init?.headers as Record<string, string>) ?? {});

  const response = await fetch(`${getApiBase()}${path}`, { ...init, headers });
  lastTraceId = response.headers.get("X-Trace-Id") ?? traceId;
  let payload: ApiEnvelope<T> | null = null;
  try {
    payload = (await response.json()) as ApiEnvelope<T>;
  } catch {
    payload = null;
  }
  return { response, payload };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const traceId = randomTraceId();
  const isAdminPath = path.startsWith("/admin/");

  const pickToken = async (forceRefresh: boolean): Promise<string | null> => {
    if (isAdminPath) {
      return getAdminToken();
    }
    if (path.startsWith("/api/")) {
      return await ensureTouristToken(forceRefresh);
    }
    return null;
  };

  let token = await pickToken(false);

  let attempt: Attempt<T>;
  try {
    attempt = await doFetch<T>(path, init, token, traceId);
  } catch (err) {
    throw new ApiError(
      err instanceof Error ? err.message : "network_error",
      "NETWORK_ERROR",
      0,
      traceId
    );
  }

  // 401 handling:
  //   - admin path: token invalid → clear + redirect to /login
  //   - tourist path: auto-refresh the anonymous token once and retry
  if (attempt.response.status === 401) {
    if (isAdminPath) {
      redirectToLogin();
    } else {
      token = await pickToken(true);
      try {
        attempt = await doFetch<T>(path, init, token, traceId);
      } catch (err) {
        throw new ApiError(
          err instanceof Error ? err.message : "network_error",
          "NETWORK_ERROR",
          0,
          traceId
        );
      }
    }
  }

  const { response, payload } = attempt;
  if (!response.ok || !payload || payload.code !== "OK") {
    throw new ApiError(
      payload?.message ?? `HTTP ${response.status}`,
      payload?.code ?? "HTTP_ERROR",
      response.status,
      payload?.trace_id ?? lastTraceId
    );
  }
  return payload.data;
}

// --- Public API -------------------------------------------------------------

export async function adminLogin(email: string, password: string): Promise<void> {
  const traceId = randomTraceId();
  const response = await fetch(`${getApiBase()}/admin/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Trace-Id": traceId },
    body: JSON.stringify({ email, password })
  });
  lastTraceId = response.headers.get("X-Trace-Id") ?? traceId;
  const payload = (await response.json()) as ApiEnvelope<{
    token: { token: string; expires_at: string };
    profile: { admin_id: string; name: string; email: string; role: string };
  }>;
  if (!response.ok || payload.code !== "OK") {
    throw new ApiError(
      payload.message ?? `HTTP ${response.status}`,
      payload.code ?? "HTTP_ERROR",
      response.status,
      payload.trace_id ?? lastTraceId
    );
  }
  write(ADMIN_KEY, payload.data.token.token);
}

export async function getDashboard() {
  try {
    return await request<DashboardOverview>("/admin/v1/dashboard/overview");
  } catch {
    return {
      active_sessions: 2847,
      token_cost_usd_today: 12.4,
      cache_hit_rate: 0.78,
      nps: 4.6
    };
  }
}

export async function getLandmarks() {
  try {
    const data = await request<{ landmarks: typeof fallbackLandmarks }>(
      "/api/v1/landmarks?scenic_id=demo-scenic"
    );
    return data.landmarks;
  } catch {
    return fallbackLandmarks;
  }
}

export async function getReplay(sessionId = "demo-session") {
  try {
    return await request<{
      session_id: string;
      events: Array<Record<string, string>>;
      retrieved_chunks: string[];
    }>(`/admin/v1/sessions/${sessionId}/replay`);
  } catch {
    return {
      session_id: sessionId,
      events: [
        { at: "00:01.2", type: "ASR 完成" },
        { at: "00:01.7", type: "RAG 检索" },
        { at: "00:02.1", type: "LLM 首 token" },
        { at: "00:02.6", type: "TTS 首音" }
      ],
      retrieved_chunks: ["seed:intro", "moon-gate:history", "route:safety"]
    };
  }
}

export const localMetrics = dashboardMetrics;


