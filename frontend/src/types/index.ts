export type Destination =
  | 'RESTROOM'
  | 'OFFICE'
  | 'NURSE'
  | 'HALLWAY'
  | 'CLASSROOM'
  | 'COUNSELOR'
  | 'OTHER';

export type AttendanceStatus =
  | 'PRESENT'
  | 'ABSENT'
  | 'TARDY'
  | 'EXCUSED'
  | 'UNEXCUSED';

export type HallPassStatus = 'ACTIVE' | 'RETURNED' | 'OVERDUE' | 'FLAGGED';

export interface Student {
  id: string;
  name: string;
  studentNumber: string;
  gradeLevel: number;
}

export interface ClassPeriod {
  id: string;
  name: string;
  subject: string;
  period: string;
  startTime: string;
  endTime: string;
  room: string;
  teacherId: string;
  studentCount: number;
  type?: 'suggested' | 'advisory' | 'lunch' | 'regular';
}

export interface HallPass {
  id: string;
  studentId: string;
  studentName: string;
  destination: Destination;
  checkedOutAt: Date;
  expectedReturnAt: Date;
  status: HallPassStatus;
}

export interface AppState {
  selectedSession: ClassPeriod | null;
  activePasses: HallPass[];
  emergencyLock: boolean;
  selectedStudent: Student | null;
  selectedDestination: Destination | null;
}

export interface AppContextType extends AppState {
  setSelectedSession: (session: ClassPeriod | null) => void;
  addHallPass: (pass: HallPass) => void;
  returnHallPass: (passId: string) => void;
  setEmergencyLock: (locked: boolean) => void;
  setSelectedStudent: (student: Student | null) => void;
  setSelectedDestination: (destination: Destination | null) => void;
}
