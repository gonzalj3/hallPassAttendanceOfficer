// Browser-side fetch helpers for the FastAPI backend.

import type {
  AlertSummaryApi,
  ClassPeriodApi,
  HallPassApi,
  RosterApi,
  VoiceCallDetailApi,
  VoiceCallSummaryApi,
} from './types';

const API_BASE: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { ...init, credentials: 'include' });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body);
    } catch {
      /* body wasn't JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

export async function listSessions(): Promise<ClassPeriodApi[]> {
  return request<ClassPeriodApi[]>('/api/sessions');
}

export async function getRoster(sessionId: string): Promise<RosterApi> {
  return request<RosterApi>(`/api/sessions/${sessionId}/students`);
}

export async function listActivePasses(): Promise<HallPassApi[]> {
  return request<HallPassApi[]>('/api/hall-passes?status_filter=ACTIVE');
}

export async function listAlerts(opts?: {
  status?: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  limit?: number;
}): Promise<AlertSummaryApi[]> {
  const qs = new URLSearchParams();
  if (opts?.status) qs.set('status_filter', opts.status);
  if (opts?.limit) qs.set('limit', String(opts.limit));
  const path = qs.toString() ? `/api/alerts?${qs}` : '/api/alerts';
  return request<AlertSummaryApi[]>(path);
}

// Voice-agent integration was removed when the project was scoped down to
// hall-pass monitoring only. These stubs keep the dashboard's UI cards
// compiling -- they always resolve to empty data so the cards render their
// empty state.
export async function listVoiceCalls(_opts?: {
  limit?: number;
  studentId?: string;
}): Promise<VoiceCallSummaryApi[]> {
  return [];
}

export async function getVoiceCall(_id: string): Promise<VoiceCallDetailApi> {
  throw new Error('voice-agent integration removed');
}
