import { fallbackLandmarks } from "@aether/design-system/demo-data";

// --- API base URL resolution -----------------------------------------------

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window === "object") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return "http://127.0.0.1:8000";
}

// --- Types ------------------------------------------------------------------

type ApiEnvelope<T> = {
  data: T;
  code: string;
  message: string;
  trace_id: string;
};

export type Landmark = {
  id: string;
  scenic_id?: string;
  name: string;
  summary: string;
  tags: string[];
};

export type Session = {
  id: string;
  scenic_id: string;
  persona_id: string;
  status: string;
};

export type RouteStop = {
  landmark_id: string;
  name: string;
  walk_minutes_from_previous: number;
  reason: string;
};

export type RoutePlan = {
  scenic_id: string;
  total_walk_minutes: number;
  stops: RouteStop[];
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

// --- Tiny client trace ------------------------------------------------------

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

// --- Auth token store (sessionStorage) --------------------------------------

const TOKEN_KEY = "aether.tourist.token";

function readToken(): string | null {
  if (typeof window !== "object") return null;
  try {
    return window.sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

function writeToken(token: string): void {
  if (typeof window !== "object") return;
  try {
    window.sessionStorage.setItem(TOKEN_KEY, token);
  } catch {
    // Safari private mode / sandboxed iframe — silently degrade.
  }
}

function clearToken(): void {
  if (typeof window !== "object") return;
  try {
    window.sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // ignored
  }
}

let bootstrapPromise: Promise<string> | null = null;

export async function ensureTouristToken(forceRefresh = false): Promise<string> {
  if (!forceRefresh) {
    const cached = readToken();
    if (cached) return cached;
  } else {
    clearToken();
  }
  if (bootstrapPromise) return bootstrapPromise;
  bootstrapPromise = (async () => {
    const traceId = randomTraceId();
    const response = await fetch(`${getApiBase()}/api/v1/auth/anonymous`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Trace-Id": traceId },
      body: "{}"
    });
    lastTraceId = response.headers.get("X-Trace-Id") ?? traceId;
    const payload = (await response.json()) as ApiEnvelope<{ token: string }>;
    const token = payload.data?.token ?? "";
    if (token) writeToken(token);
    bootstrapPromise = null;
    return token;
  })();
  return bootstrapPromise;
}

// --- Core request helper ----------------------------------------------------

async function doFetch<T>(
  path: string,
  init: RequestInit | undefined,
  token: string,
  traceId: string
): Promise<{ response: Response; payload: ApiEnvelope<T> | null }> {
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
  let token = await ensureTouristToken();

  let attempt: { response: Response; payload: ApiEnvelope<T> | null };
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

  // 401 → token expired or invalid: drop cache, bootstrap fresh, retry once.
  if (attempt.response.status === 401) {
    token = await ensureTouristToken(true);
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

  const { response, payload } = attempt;
  if (!response.ok || !payload || payload.code !== "OK") {
    const message = payload?.message ?? `HTTP ${response.status}`;
    const code = payload?.code ?? "HTTP_ERROR";
    throw new ApiError(message, code, response.status, payload?.trace_id ?? lastTraceId);
  }
  return payload.data;
}

// --- Public API surface -----------------------------------------------------

export async function createSession(scenicId = "demo-scenic") {
  return request<Session>("/api/v1/sessions", {
    method: "POST",
    body: JSON.stringify({
      scenic_id: scenicId,
      user_id: "linjing-demo",
      locale: "zh-CN",
      idempotency_key: `linjing-${Date.now()}`
    })
  });
}

export async function getLandmarks(scenicId = "demo-scenic") {
  try {
    const data = await request<{ landmarks: Landmark[] }>(
      `/api/v1/landmarks?scenic_id=${encodeURIComponent(scenicId)}`
    );
    return data.landmarks;
  } catch {
    return fallbackLandmarks;
  }
}

export async function getRoute(scenicId = "demo-scenic") {
  try {
    return await request<RoutePlan>(
      `/api/v1/recommendations/route?scenic_id=${encodeURIComponent(scenicId)}`
    );
  } catch {
    return {
      scenic_id: scenicId,
      total_walk_minutes: 16,
      stops: fallbackLandmarks.slice(0, 3).map((landmark, index) => ({
        landmark_id: landmark.id,
        name: landmark.name,
        walk_minutes_from_previous: index === 0 ? 0 : 8,
        reason: landmark.summary
      }))
    };
  }
}

export type WsConnectInfo = {
  url: string;
  /** Pass these as the second argument to `new WebSocket(url, protocols)`. */
  protocols: string[];
};

export async function wsUrl(sessionId: string): Promise<WsConnectInfo> {
  const token = await ensureTouristToken();
  const base = new URL(getApiBase());
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = `/api/v1/sessions/${sessionId}/stream`;
  // Prefer subprotocol auth so the JWT never lands in proxy logs / referer.
  // Backend (authenticate_websocket) reads `bearer.<jwt>` from
  // Sec-WebSocket-Protocol and echoes it back.
  return {
    url: base.toString(),
    protocols: token ? [`bearer.${token}`] : []
  };
}

