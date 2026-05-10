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
  const res = await fetch(`${API_BASE}${path}`, init);
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

export async function listVoiceCalls(opts?: {
  limit?: number;
  studentId?: string;
}): Promise<VoiceCallSummaryApi[]> {
  const qs = new URLSearchParams();
  if (opts?.limit) qs.set('limit', String(opts.limit));
  if (opts?.studentId) qs.set('student_id', opts.studentId);
  const path = qs.toString() ? `/api/voice-calls?${qs}` : '/api/voice-calls';
  return request<VoiceCallSummaryApi[]>(path);
}

export async function getVoiceCall(id: string): Promise<VoiceCallDetailApi> {
  return request<VoiceCallDetailApi>(`/api/voice-calls/${id}`);
}
