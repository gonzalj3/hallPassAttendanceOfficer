// Mock data for the admin dashboard. Swap these exports with API calls
// (e.g. via TanStack Query) when the backend endpoints are live.

export type ActivePass = {
  id: string;
  studentName: string;
  destination: 'Restroom' | 'Nurse' | 'Office' | 'Hallway' | 'Classroom';
  classroom: string;
  startedAt: string; // ISO timestamp
  thresholdSeconds: number;
};

export type TopStudent = {
  id: string;
  name: string;
  initials: string;
  passCount: number;
  trend: 'up' | 'down' | 'flat';
};

export type ClassroomVolume = {
  id: string;
  teacherName: string;
  room: string;
  passCount: number;
};

export type CapacityRow = {
  destination: string;
  current: number;
  limit: number | null;
  status: 'full' | 'available' | 'unlimited';
};

const ago = (seconds: number) =>
  new Date(Date.now() - seconds * 1000).toISOString();

export const mockKpis = {
  absent: 23,
  outNow: 12,
  todayTotal: 187,
  activeFlags: 3,
  avgDurationSeconds: 272,
};

export const mockActivePasses: ActivePass[] = [
  { id: '1', studentName: 'Marcus Thompson', destination: 'Restroom', classroom: 'Rm 204', startedAt: ago(862), thresholdSeconds: 300 },
  { id: '2', studentName: 'Aisha Patel',     destination: 'Nurse',    classroom: 'Rm 112', startedAt: ago(368), thresholdSeconds: 600 },
  { id: '3', studentName: 'Jayden Rivera',   destination: 'Office',   classroom: 'Rm 308', startedAt: ago(161), thresholdSeconds: 600 },
  { id: '4', studentName: 'Sofia Chen',      destination: 'Hallway',  classroom: 'Rm 215', startedAt: ago(75),  thresholdSeconds: 300 },
  { id: '5', studentName: "Tyler O'Brien",   destination: 'Restroom', classroom: 'Rm 109', startedAt: ago(48),  thresholdSeconds: 300 },
];

export const mockTopStudents: TopStudent[] = [
  { id: '1', name: 'Marcus Thompson', initials: 'MT', passCount: 8, trend: 'up' },
  { id: '2', name: 'Aisha Patel',     initials: 'AP', passCount: 7, trend: 'flat' },
  { id: '3', name: 'Jayden Rivera',   initials: 'JR', passCount: 6, trend: 'flat' },
  { id: '4', name: 'Sofia Chen',      initials: 'SC', passCount: 6, trend: 'flat' },
  { id: '5', name: "Tyler O'Brien",   initials: 'TO', passCount: 5, trend: 'flat' },
];

export const mockClassroomVolume: ClassroomVolume[] = [
  { id: '1', teacherName: 'Mr. Garcia', room: 'Rm 204', passCount: 34 },
  { id: '2', teacherName: 'Ms. Patel',  room: 'Rm 112', passCount: 29 },
  { id: '3', teacherName: 'Mr. Cohen',  room: 'Rm 308', passCount: 24 },
  { id: '4', teacherName: 'Ms. Reyes',  room: 'Rm 215', passCount: 22 },
  { id: '5', teacherName: 'Mr. Brooks', room: 'Rm 109', passCount: 19 },
];

export const mockCapacity: CapacityRow[] = [
  { destination: 'Restroom', current: 2, limit: 2,    status: 'full' },
  { destination: 'Nurse',    current: 1, limit: 3,    status: 'available' },
  { destination: 'Office',   current: 2, limit: 5,    status: 'available' },
  { destination: 'Hallway',  current: 7, limit: null, status: 'unlimited' },
];

export const mockHourlyToday = [3, 8, 11, 13, 18, 22, 17, 11, 5];
export const mockHourlyAvg   = [4, 7,  9, 10, 13, 18, 14, 10, 6];
export const hourLabels      = ['8a', '9a', '10a', '11a', '12p', '1p', '2p', '3p', '4p'];
