// Browser-side fetch helpers for the FastAPI backend.
//
// In production we use RELATIVE URLs (API_BASE = '') so requests go
// through the Netlify proxy redirects (netlify.toml) and the session
// cookie lives on the Netlify origin -- first-party, not blocked by
// Safari ITP / Chrome privacy sandbox.
//
// In local dev we hit the FastAPI process directly on localhost:8000
// (set VITE_API_URL in frontend/.env.local to change the port).

import type { Destination, HallPass } from '../types';
import type {
  ClassPeriodApi,
  HallPassApi,
  IssueHallPassRequest,
  RosterApi,
} from './types';

function defaultApiBase(): string {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'http://localhost:8000';
    }
  }
  return '';
}

const API_BASE: string =
  (import.meta.env.VITE_API_URL as string | undefined) ?? defaultApiBase();

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body);
    } catch {
      // body wasn't JSON — keep statusText
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

// ---- ClassSession / Roster ----

export async function listSessions(): Promise<ClassPeriodApi[]> {
  return request<ClassPeriodApi[]>('/api/sessions');
}

export async function getRoster(sessionId: string): Promise<RosterApi> {
  return request<RosterApi>(`/api/sessions/${sessionId}/students`);
}

// ---- Hall passes ----

function hydrateHallPass(p: HallPassApi): HallPass {
  return {
    id: p.id,
    studentId: p.studentId,
    studentName: p.studentName,
    destination: p.destination as Destination,
    checkedOutAt: new Date(p.checkedOutAt),
    expectedReturnAt: new Date(p.expectedReturnAt),
    status: p.status,
  };
}

export async function issueHallPass(req: IssueHallPassRequest): Promise<HallPass> {
  const raw = await request<HallPassApi>('/api/hall-passes', {
    method: 'POST',
    body: JSON.stringify(req),
  });
  return hydrateHallPass(raw);
}

export async function returnHallPass(passId: string): Promise<HallPass> {
  const raw = await request<HallPassApi>(`/api/hall-passes/${passId}/return`, {
    method: 'POST',
  });
  return hydrateHallPass(raw);
}

export function hydrateActivePasses(roster: RosterApi): HallPass[] {
  return roster.activePasses.map(hydrateHallPass);
}
