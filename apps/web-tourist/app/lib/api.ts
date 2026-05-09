import { fallbackLandmarks } from "@aether/design-system/demo-data";

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window === "object") return `${window.location.protocol}//${window.location.hostname}:8000`;
  return "http://127.0.0.1:8000";
}

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.code !== "OK") {
    throw new Error(payload.message || "服务暂时不可用，已切换本地演示数据。");
  }
  return payload.data;
}

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

export function wsUrl(sessionId: string) {
  const base = new URL(getApiBase());
  base.protocol = base.protocol === "https:" ? "wss:" : "ws:";
  base.pathname = `/api/v1/sessions/${sessionId}/stream`;
  return base.toString();
}
