import type {
  CreateSessionResponse,
  EndSessionResponse,
  HumeTokenResponse,
  GraphSnapshotResponse,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const msg =
      body?.detail?.message ?? body?.detail ?? `HTTP ${res.status}`;
    throw new Error(String(msg));
  }
  return res.json() as Promise<T>;
}

export async function createSession(): Promise<CreateSessionResponse> {
  return apiFetch<CreateSessionResponse>("/v1/sessions", {
    method: "POST",
    body: "{}",
  });
}

export async function endSession(sessionId: string): Promise<EndSessionResponse> {
  return apiFetch<EndSessionResponse>(`/v1/sessions/${sessionId}/end`, {
    method: "POST",
  });
}

export async function getHumeToken(): Promise<HumeTokenResponse> {
  return apiFetch<HumeTokenResponse>("/v1/hume/access-token", {
    method: "POST",
  });
}

export async function getGraphSnapshot(
  sessionId: string
): Promise<GraphSnapshotResponse> {
  return apiFetch<GraphSnapshotResponse>(`/v1/sessions/${sessionId}/graph`);
}
