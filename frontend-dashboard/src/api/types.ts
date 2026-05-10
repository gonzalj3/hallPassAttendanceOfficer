// Wire shapes returned by the FastAPI backend at /api/*. Mirrors
// `src/hpao/schemas/frontend.py` byte-for-byte.

export type ClassPeriodType = 'suggested' | 'advisory' | 'lunch' | 'regular';
export type HallPassStatus = 'ACTIVE' | 'RETURNED' | 'OVERDUE' | 'FLAGGED';
export type Destination =
  | 'RESTROOM'
  | 'NURSE'
  | 'COUNSELOR'
  | 'OFFICE'
  | 'OTHER'
  | 'HALLWAY'
  | 'CLASSROOM';
export type Severity = 'low' | 'medium' | 'high' | 'critical';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
export type VoiceCallScenario = 'absentee' | 'hall_pass' | 'other';

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

export interface VoiceCallSummaryApi {
  id: string;
  correlationId: string;
  studentId: string;
  studentName: string;
  alertId: string | null;
  scenario: VoiceCallScenario;
  callStartedAt: string;
  callEndedAt: string;
  excuseSummary: string | null;
  parentConfirmed: boolean | null;
  language: string | null;
  createdAt: string;
}

export interface TranscriptTurnApi {
  speaker: string;
  text: string;
  occurredAt: string | null;
}

export interface VoiceCallDetailApi extends VoiceCallSummaryApi {
  transcript: TranscriptTurnApi[];
}

export interface AlertSummaryApi {
  id: string;
  studentId: string;
  studentName: string;
  ruleKey: string;
  severity: Severity;
  status: AlertStatus;
  context: Record<string, unknown>;
  createdAt: string;
}

export interface RealtimeEnvelope {
  channel: string;
  event: RealtimeEvent;
}

export type RealtimeEventName =
  | 'attendance.recorded'
  | 'hallpass.issued'
  | 'hallpass.returned'
  | 'hallpass.overdue'
  | 'alert.raised'
  | 'voice_call.completed';

export interface RealtimeEvent {
  event: RealtimeEventName;
  event_id: string;
  occurred_at: string;
  school_id: string;
  student_id: string;
  [key: string]: unknown;
}
