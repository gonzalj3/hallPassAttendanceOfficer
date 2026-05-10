// Bridge between the FastAPI /api/* shapes and the dashboard's existing
// display types. Keeps the rendering code in AdminDashboard.tsx unchanged
// while swapping mockAdmin.ts for live data + WS-driven live updates.

import { useCallback, useEffect, useMemo, useState } from 'react';

import { listActivePasses, listAlerts, listVoiceCalls, getRoster, listSessions, ApiError } from '../api/client';
import { useRealtime } from '../api/realtime';
import type {
  AlertSummaryApi,
  Destination as ApiDestination,
  HallPassApi,
  RealtimeEnvelope,
  RosterApi,
  VoiceCallSummaryApi,
} from '../api/types';
import type {
  ActivePass,
  ClassRoster,
  OutLocation,
  OutOfClassEntry,
  RosterStudent,
  StudentLocation,
} from '../data/mockAdmin';

// ---- conversion helpers ----

const DEST_DISPLAY: Record<ApiDestination, OutLocation | 'Other'> = {
  RESTROOM: 'Restroom',
  NURSE: 'Nurse',
  OFFICE: 'Office',
  HALLWAY: 'Hallway',
  CLASSROOM: 'Classroom' as OutLocation,
  COUNSELOR: 'Office',
  OTHER: 'Other',
};

const THRESHOLD_SECS: Record<OutLocation | 'Other', number> = {
  Restroom: 300,
  Hallway: 300,
  Nurse: 600,
  Office: 600,
  Classroom: 600,
  Other: 600,
} as Record<OutLocation | 'Other', number>;

function destToDisplay(d: ApiDestination): OutLocation {
  // The dashboard's OutLocation only has 4 values; map COUNSELOR/OTHER/CLASSROOM
  // onto the closest visible bucket so we don't leak unknown labels into the UI.
  return (DEST_DISPLAY[d] === 'Other' ? 'Office' : DEST_DISPLAY[d]) as OutLocation;
}

function passToActive(p: HallPassApi): ActivePass {
  const dest = destToDisplay(p.destination);
  return {
    id: p.id,
    studentName: p.studentName,
    destination: dest as ActivePass['destination'],
    classroom: '', // not in /api/hall-passes; UI only uses it as a label, ok empty
    startedAt: p.checkedOutAt,
    thresholdSeconds: THRESHOLD_SECS[dest],
  };
}

function rosterToClassRoster(r: RosterApi): ClassRoster {
  // Build a Set of currently-out studentIds from this session's active passes.
  const outById = new Map<string, { dest: OutLocation; sinceSec: number }>();
  for (const p of r.activePasses) {
    const dest = destToDisplay(p.destination);
    const sinceSec = Math.max(
      0,
      Math.floor((Date.now() - new Date(p.checkedOutAt).getTime()) / 1000),
    );
    outById.set(p.studentId, { dest, sinceSec });
  }

  const students: RosterStudent[] = r.students.map((s) => {
    const out = outById.get(s.id);
    if (out) {
      return {
        id: s.id,
        name: s.name,
        location: out.dest as StudentLocation,
        outSinceSeconds: out.sinceSec,
      };
    }
    return { id: s.id, name: s.name, location: 'in_class' };
  });

  return {
    id: r.session.classId,
    className: r.session.name,
    teacherName: 'Teacher', // /api/sessions exposes teacherId not name; placeholder
    room: r.session.room || '',
    students,
  };
}

export interface DashboardData {
  loading: boolean;
  error: string | null;
  activePasses: ActivePass[];
  classRosters: ClassRoster[];
  outOfClass: OutOfClassEntry[];
  voiceCalls: VoiceCallSummaryApi[];
  alerts: AlertSummaryApi[];
  /** All distinct schoolIds the data references — used to set up WS channels. */
  schoolIds: string[];
  refresh: () => void;
}

export function useDashboardData(): DashboardData {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activePasses, setActivePasses] = useState<ActivePass[]>([]);
  const [classRosters, setClassRosters] = useState<ClassRoster[]>([]);
  const [voiceCalls, setVoiceCalls] = useState<VoiceCallSummaryApi[]>([]);
  const [alerts, setAlerts] = useState<AlertSummaryApi[]>([]);
  const [schoolIds, setSchoolIds] = useState<string[]>([]);

  const fetchAll = useCallback(async () => {
    try {
      setError(null);
      const [sessions, passes, calls, alertsList] = await Promise.all([
        listSessions(),
        listActivePasses(),
        listVoiceCalls({ limit: 25 }),
        listAlerts({ limit: 50 }),
      ]);

      // Hydrate per-session rosters in parallel.
      const rosters = await Promise.all(sessions.map((s) => getRoster(s.id)));
      setClassRosters(rosters.map(rosterToClassRoster));
      setActivePasses(passes.map(passToActive));
      setVoiceCalls(calls);
      setAlerts(alertsList);
      setSchoolIds(Array.from(new Set(sessions.map((s) => s.schoolId))));
    } catch (e: unknown) {
      const msg = e instanceof ApiError ? `${e.status} ${e.message}` : (e as Error).message;
      setError(`Failed to load dashboard: ${msg}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchAll();
  }, [fetchAll]);

  // Live updates: any school-channel event triggers a coarse refetch.
  // For demo scale (one school, dozens of students) this is well within
  // budget; later we could narrow per-event-type updates to avoid the
  // full reload.
  const channels = useMemo(() => schoolIds.map((id) => `school:${id}`), [schoolIds]);
  useRealtime({
    channels,
    onEvent: (envelope: RealtimeEnvelope) => {
      const name = envelope.event?.event;
      if (
        name === 'hallpass.issued' ||
        name === 'hallpass.returned' ||
        name === 'hallpass.overdue' ||
        name === 'alert.raised' ||
        name === 'voice_call.completed'
      ) {
        void fetchAll();
      }
    },
  });

  const outOfClass: OutOfClassEntry[] = useMemo(() => {
    const out: OutOfClassEntry[] = [];
    for (const cls of classRosters) {
      for (const s of cls.students) {
        if (s.location === 'in_class') continue;
        if (s.outSinceSeconds === undefined) continue;
        out.push({
          studentId: s.id,
          name: s.name,
          classId: cls.id,
          className: cls.className,
          teacherName: cls.teacherName,
          room: cls.room,
          destination: s.location as OutLocation,
          outSinceSeconds: s.outSinceSeconds,
          thresholdSeconds: THRESHOLD_SECS[s.location as OutLocation] ?? 300,
        });
      }
    }
    return out;
  }, [classRosters]);

  return {
    loading,
    error,
    activePasses,
    classRosters,
    outOfClass,
    voiceCalls,
    alerts,
    schoolIds,
    refresh: fetchAll,
  };
}
