// Browser-side fetch helpers for the FastAPI backend.
//
// All fetches use RELATIVE URLs. In dev, vite.config.ts proxies
// /api, /auth, /v1 to localhost:8000. In prod, netlify.toml's
// [[redirects]] proxy the same paths to Railway. The session cookie
// lives on the page's origin (first-party) so it's not blocked by
// browser cross-site cookie policies. No env vars consulted -- a
// stale VITE_API_URL in a CI dashboard can't break sign-in.

import type { Destination, HallPass } from '../types';
import type {
  ClassPeriodApi,
  HallPassApi,
  IssueHallPassRequest,
  RosterApi,
} from './types';

const API_BASE = '';

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
