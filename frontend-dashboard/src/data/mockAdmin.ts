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

export type OutLocation = 'Restroom' | 'Nurse' | 'Office' | 'Hallway';
export type StudentLocation = 'in_class' | OutLocation;

export type RosterStudent = {
  id: string;
  name: string;
  location: StudentLocation;
  /** seconds since they left class; only set when location !== 'in_class' */
  outSinceSeconds?: number;
};

export type ClassRoster = {
  id: string;
  className: string;
  teacherName: string;
  room: string;
  students: RosterStudent[];
};

const thresholdFor = (loc: OutLocation): number =>
  loc === 'Restroom' || loc === 'Hallway' ? 300 : 600;

const buildRoster = (
  id: string,
  className: string,
  teacherName: string,
  room: string,
  inClass: string[],
  out: Array<[string, OutLocation, number]>,
): ClassRoster => {
  const students: RosterStudent[] = [
    ...inClass.map((name, i) => ({
      id: `${id}-in-${i}`,
      name,
      location: 'in_class' as StudentLocation,
    })),
    ...out.map(([name, loc, sec], i) => ({
      id: `${id}-out-${i}`,
      name,
      location: loc,
      outSinceSeconds: sec,
    })),
  ];
  return { id, className, teacherName, room, students };
};

export const mockClassRosters: ClassRoster[] = [
  buildRoster(
    'c1', 'Algebra II', 'Mr. Garcia', 'Rm 204',
    [
      'Emma Rodriguez', 'Liam Foster', 'Ava Santos', 'Noah Bennett',
      'Isabella Torres', 'Mason Reilly', 'Amelia Schmidt', 'James Patel',
      'Harper Anderson', 'Benjamin Cole', 'Evelyn Yamada', 'Lucas Hernandez',
      'Charlotte Wu',
    ],
    [
      ['Marcus Thompson', 'Restroom', 862],
      ['Logan Ortiz', 'Hallway', 134],
      ['Mia Johnson', 'Nurse', 320],
      ['Ethan Kim', 'Office', 55],
      ['Olivia Park', 'Restroom', 175],
    ],
  ),
  buildRoster(
    'c2', 'Biology', 'Ms. Patel', 'Rm 112',
    [
      'Daniel Lee', 'Sophia Garcia', 'Madison Wright', 'Carter Roberts',
      'Layla Brown', 'Owen Murphy', 'Zoe Walker', 'Caleb Diaz',
      'Grace Sullivan', 'Sebastian Hayes', 'Aria Mitchell',
    ],
    [
      ['Aisha Patel', 'Nurse', 368],
      ['Jackson Cole', 'Restroom', 412],
      ['Riley Cooper', 'Office', 95],
      ['Lily Nguyen', 'Hallway', 200],
      ['Henry Adams', 'Restroom', 142],
    ],
  ),
  buildRoster(
    'c3', 'US History', 'Mr. Cohen', 'Rm 308',
    [
      'Mateo Sanchez', 'Avery Bell', 'Jasmine Hill', 'Cameron Brooks',
      'Penelope Wong', 'Aiden Castillo', 'Stella Foster', 'Jonah Reed',
      'Elise Carter', 'Eli Bauer', 'Brooks Tanner', 'Hazel Chen',
      'Andre Watson',
    ],
    [
      ['Jayden Rivera', 'Office', 161],
      ['Maya Singh', 'Restroom', 587],
      ['Naomi Ross', 'Hallway', 35],
      ['Theodore Wells', 'Restroom', 320],
    ],
  ),
  buildRoster(
    'c4', 'English Lit', 'Ms. Reyes', 'Rm 215',
    [
      'Connor Bailey', 'Ruby Vasquez', 'Kai Robinson', 'Chloe Edwards',
      'Lily Clark', 'Eliza Sharma', 'Tobias Jensen', 'Isla Crawford',
      'Adrian Vega',
    ],
    [
      ['Sofia Chen', 'Hallway', 75],
      ['Phoenix Khan', 'Restroom', 240],
      ['Diego Ramirez', 'Nurse', 480],
      ['Wyatt Morgan', 'Office', 22],
      ['Bea Larson', 'Restroom', 60],
      ['Jude Cabrera', 'Hallway', 12],
    ],
  ),
  buildRoster(
    'c5', 'Chemistry', 'Mr. Brooks', 'Rm 109',
    [
      'Quinn Holloway', 'Camila Davis', 'Nathan Pierce', 'Ivy Lambert',
      'Ezra Sutton', 'Aria Patel', 'Ronan McKay', 'Levi Townsend',
      'Dashiell Vance', 'Tessa Nakamura', 'Cassius Webb',
    ],
    [
      ["Tyler O'Brien", 'Restroom', 48],
      ['Felix Donovan', 'Restroom', 720],
      ['Skyler Ortega', 'Office', 65],
      ['Margot Reilly', 'Hallway', 150],
      ['Juno Beck', 'Hallway', 95],
    ],
  ),
  buildRoster(
    'c6', 'Spanish III', 'Ms. Nguyen', 'Rm 220',
    [
      'Astrid Lindgren', 'Mateo Cruz', 'Bianca Ferrari', 'Otto Schwartz',
      'Lev Ivanov', 'Inez Solis', 'Beckett Pierce', 'Romy Drake',
      'Bodhi Gilbert', 'Saoirse Lynch', 'Knox Eddington',
    ],
    [
      ['Mira Reyes', 'Restroom', 195],
      ['Cleo Bates', 'Hallway', 30],
      ['Hiro Tanaka', 'Restroom', 380],
    ],
  ),
  buildRoster(
    'c7', 'Geometry', 'Mr. Davis', 'Rm 305',
    [
      'Reagan Hart', 'Tobias Vance', 'Wesley Knight', 'Niko Pavlov',
      'Greta Olsen', 'Caspian Reid', 'Nash Coleman', 'Augustin Royal',
      'Juniper Reeves', 'Ridge Calloway',
    ],
    [
      ['Sage Whitley', 'Restroom', 510],
      ['Coral Brennan', 'Nurse', 60],
      ['Marlowe Crane', 'Restroom', 280],
      ['Vera Ash', 'Hallway', 170],
      ['Maren Doyle', 'Office', 22],
      ['Indie Tran', 'Nurse', 75],
    ],
  ),
  buildRoster(
    'c8', 'World History', 'Ms. Williams', 'Rm 118',
    [
      'Ezekiel Pierce', 'Nova Castellanos', 'Atlas Krieger', 'Magnus Holt',
      'Persephone Vale', 'Orion Marsh', 'Soren Marlowe', 'Esme Tatum',
      'Linus Beck', 'Rowan Stout',
    ],
    [
      ['Roman Veliotis', 'Restroom', 645],
      ['Iris Ashford', 'Hallway', 110],
      ['Calliope Yates', 'Nurse', 415],
      ['Wren Bishop', 'Restroom', 220],
    ],
  ),
];

export type OutOfClassEntry = {
  studentId: string;
  name: string;
  classId: string;
  className: string;
  teacherName: string;
  room: string;
  destination: OutLocation;
  outSinceSeconds: number;
  thresholdSeconds: number;
};

export const mockOutOfClass: OutOfClassEntry[] = mockClassRosters.flatMap((cls) =>
  cls.students
    .filter((s): s is RosterStudent & { location: OutLocation; outSinceSeconds: number } =>
      s.location !== 'in_class' && s.outSinceSeconds !== undefined,
    )
    .map((s) => ({
      studentId: s.id,
      name: s.name,
      classId: cls.id,
      className: cls.className,
      teacherName: cls.teacherName,
      room: cls.room,
      destination: s.location,
      outSinceSeconds: s.outSinceSeconds,
      thresholdSeconds: thresholdFor(s.location),
    })),
);

const ago = (seconds: number) =>
  new Date(Date.now() - seconds * 1000).toISOString();

export const mockActivePasses: ActivePass[] = mockOutOfClass.map((o, i) => ({
  id: String(i + 1),
  studentName: o.name,
  destination: o.destination,
  classroom: o.room,
  startedAt: ago(o.outSinceSeconds),
  thresholdSeconds: o.thresholdSeconds,
}));

const totalStudents = mockClassRosters.reduce((n, c) => n + c.students.length, 0);
const flaggedNow = mockOutOfClass.filter((o) => o.outSinceSeconds > o.thresholdSeconds).length;

export const mockKpis = {
  outNow: mockOutOfClass.length,
  todayTotal: 187,
  activeFlags: flaggedNow,
  avgDurationSeconds: 272,
  adoptionPct: 78,
  lockdowns: 0,
  totalStudents,
  absent: 12,
};

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

export const mockHourlyToday = [3, 8, 11, 13, 18, 22, 17, 11, 5];
export const mockHourlyAvg   = [4, 7,  9, 10, 13, 18, 14, 10, 6];
export const hourLabels      = ['8a', '9a', '10a', '11a', '12p', '1p', '2p', '3p', '4p'];
