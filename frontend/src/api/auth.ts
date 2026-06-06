// Role-picker auth: signs in as the seeded demo Teacher or Principal
// and stores the session in an HttpOnly cookie set by the backend.
// Always relative URLs -- vite proxy (dev) or netlify rewrite (prod)
// gets the request to FastAPI. Session cookie is first-party either way.

const API_BASE = '';

export type DemoRole = 'TEACHER' | 'ADMIN';

export interface CurrentUser {
  user_id: string;
  school_id: string;
  role: DemoRole;
  name: string;
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`auth ${res.status}: ${detail.slice(0, 200)}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function signIn(role: DemoRole): Promise<CurrentUser> {
  return authRequest<CurrentUser>('/auth/role-pick', {
    method: 'POST',
    body: JSON.stringify({ role }),
  });
}

export async function getMe(): Promise<CurrentUser | null> {
  try {
    return await authRequest<CurrentUser>('/auth/me');
  } catch {
    return null;
  }
}

export function signOut(): Promise<void> {
  return authRequest<void>('/auth/logout', { method: 'POST' });
}
