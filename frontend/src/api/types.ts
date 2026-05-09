// Shapes returned by the FastAPI backend at /api/*. Mirrors
// `src/hpao/schemas/frontend.py` byte-for-byte.

import type { Destination, HallPassStatus } from '../types';

export type ClassPeriodType = 'suggested' | 'advisory' | 'lunch' | 'regular';

export interface ClassPeriodApi {
  id: string;
  classId: string;
  schoolId: string;
  name: string;
  subject: string;
  period: string;
  startTime: string;
  endTime: string;
  room: string;
  teacherId: string;
  studentCount: number;
  type: ClassPeriodType;
}

export interface StudentApi {
  id: string;
  name: string;
  studentNumber: string;
  gradeLevel: number;
}

export interface HallPassApi {
  id: string;
  studentId: string;
  studentName: string;
  destination: Destination;
  checkedOutAt: string;
  expectedReturnAt: string;
  checkedInAt: string | null;
  status: HallPassStatus;
}

export interface RosterApi {
  session: ClassPeriodApi;
  students: StudentApi[];
  activePasses: HallPassApi[];
}

export interface IssueHallPassRequest {
  studentId: string;
  sessionId: string;
  destination: Destination;
  reason?: string;
  durationMinutes?: number;
}

// Realtime envelope from the WebSocket endpoint.
export interface RealtimeEnvelope {
  channel: string;
  event: RealtimeEvent;
}

export type RealtimeEventName =
  | 'attendance.recorded'
  | 'hallpass.issued'
  | 'hallpass.returned'
  | 'hallpass.overdue'
  | 'alert.raised';

export interface RealtimeEvent {
  event: RealtimeEventName;
  event_id: string;
  occurred_at: string;
  school_id: string;
  student_id: string;
  // Discriminated payloads have additional fields per event type — see
  // `src/hpao/realtime/events.py`. We treat them as opaque here and let
  // each consumer narrow as needed.
  [key: string]: unknown;
}
