import { dashboardMetrics, fallbackLandmarks } from "@aether/design-system/demo-data";

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_BASE) return process.env.NEXT_PUBLIC_API_BASE;
  if (typeof window !== "undefined") return `${window.location.protocol}//${window.location.hostname}:8000`;
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

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, {
    headers: { "Content-Type": "application/json" }
  });
  const payload = (await response.json()) as ApiEnvelope<T>;
  if (!response.ok || payload.code !== "OK") {
    throw new Error(payload.message || "服务暂时不可用，已切换本地演示数据。");
  }
  return payload.data;
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

