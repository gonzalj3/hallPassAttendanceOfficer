import { useEffect, useMemo, useState } from 'react';
import {
  mockKpis,
  mockTopStudents,
  mockClassroomVolume,
  mockHourlyToday,
  mockHourlyAvg,
  hourLabels,
  type ActivePass,
  type ClassroomVolume,
  type TopStudent,
  type OutLocation,
  type ClassRoster,
  type OutOfClassEntry,
} from '../data/mockAdmin';
import { useDashboardData } from '../hooks/useDashboardData';
import type { VoiceCallSummaryApi } from '../api/types';
import { getVoiceCall } from '../api/client';
import type { TranscriptTurnApi } from '../api/types';

type DateRange = 'today' | 'week' | 'month';

type SectionKey =
  | 'overview'
  | 'live_rosters'
  | 'live_activity'
  | 'attendance'
  | 'students'
  | 'classrooms'
  | 'alerts'
  | 'reports'
  | 'settings';

const formatElapsed = (s: number) =>
  `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

const elapsedSec = (iso: string, now: number) =>
  Math.max(0, Math.floor((now - new Date(iso).getTime()) / 1000));

const RANGE_MULTIPLIER: Record<DateRange, number> = {
  today: 1,
  week: 5,
  month: 22,
};

const RANGE_AVG_DURATION: Record<DateRange, number> = {
  today: mockKpis.avgDurationSeconds,
  week: 298,
  month: 311,
};

const RANGE_ADOPTION: Record<DateRange, number> = {
  today: mockKpis.adoptionPct,
  week: 81,
  month: 84,
};

type Kpis = {
  outNow: number;
  totalLabel: string;
  total: number;
  activeFlags: number;
  avgDurationSeconds: number;
  adoptionPct: number;
  lockdowns: number;
};

const kpisFor = (range: DateRange, flaggedNow: number): Kpis => {
  const m = RANGE_MULTIPLIER[range];
  return {
    outNow: mockKpis.outNow,
    totalLabel: range === 'today' ? 'Today Total' : range === 'week' ? 'Week Total' : 'Month Total',
    total: mockKpis.todayTotal * m,
    activeFlags:
      range === 'today' ? flaggedNow : range === 'week' ? 11 : 38,
    avgDurationSeconds: RANGE_AVG_DURATION[range],
    adoptionPct: RANGE_ADOPTION[range],
    lockdowns: range === 'month' ? 1 : 0,
  };
};

const classroomVolumeFor = (range: DateRange): ClassroomVolume[] => {
  const m = RANGE_MULTIPLIER[range];
  return mockClassroomVolume.map((c) => ({ ...c, passCount: c.passCount * m }));
};

const topStudentsFor = (range: DateRange): TopStudent[] => {
  const m = RANGE_MULTIPLIER[range];
  return mockTopStudents.map((s) => ({ ...s, passCount: s.passCount * m }));
};

const OUT_LOCATIONS: OutLocation[] = ['Restroom', 'Nurse', 'Office', 'Hallway'];

const SECTION_TITLES: Record<SectionKey, string> = {
  overview: 'Operations Overview',
  live_rosters: 'Live Rosters',
  live_activity: 'Live Activity — All Active Passes',
  attendance: 'Attendance',
  students: 'Students',
  classrooms: 'Classrooms',
  alerts: 'Alerts',
  reports: 'Reports',
  settings: 'Settings',
};

export default function AdminDashboard() {
  const [range, setRange] = useState<DateRange>('today');
  const [section, setSection] = useState<SectionKey>('overview');
  const [now, setNow] = useState(Date.now());

  // Live data from the ABE backend. Replaces every mockActivePasses /
  // mockClassRosters / mockOutOfClass usage; voice calls + alerts are new.
  const data = useDashboardData();

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  const flaggedNow = useMemo(
    () =>
      data.activePasses.filter((p) => elapsedSec(p.startedAt, now) > p.thresholdSeconds)
        .length,
    [now, data.activePasses],
  );

  const kpis = useMemo(() => {
    const base = kpisFor(range, flaggedNow);
    return range === 'today'
      ? { ...base, outNow: data.outOfClass.length }
      : base;
  }, [range, flaggedNow, data.outOfClass.length]);
  const classroomVolume = useMemo(() => classroomVolumeFor(range), [range]);
  const topStudents = useMemo(() => topStudentsFor(range), [range]);

  const showRangeFilter = section === 'overview';

  return (
    <div className="min-h-screen bg-[#e9eff0] flex font-['Atkinson_Hyperlegible_Next',sans-serif] text-[#171d1e]">
      <Sidebar
        flaggedNow={flaggedNow}
        section={section}
        onSelect={setSection}
      />
      <main className="flex-1 p-6">
        <TopBar
          range={range}
          setRange={setRange}
          section={section}
          showRangeFilter={showRangeFilter}
        />
        {data.error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {data.error}. Showing placeholder volume / leaderboard until backend reconnects.
          </div>
        )}
        {section === 'overview' && (
          <>
            <KpiStrip kpis={kpis} />
            <div className="grid grid-cols-12 gap-5">
              <LiveActivityCard
                passes={data.activePasses}
                now={now}
                onViewAll={() => setSection('live_activity')}
              />
              <ClassroomVolumeCard volume={classroomVolume} range={range} />
              <HourlyChartCard range={range} />
              <FrequentFlyersCard students={topStudents} range={range} />
              <VoiceCallsCard calls={data.voiceCalls} />
            </div>
          </>
        )}
        {section === 'live_rosters' && (
          <LiveRostersPage
            now={now}
            classRosters={data.classRosters}
            outOfClass={data.outOfClass}
          />
        )}
        {section === 'live_activity' && (
          <LiveActivityFullPage
            passes={data.activePasses}
            now={now}
            onBack={() => setSection('overview')}
          />
        )}
        {section === 'attendance' && <AttendancePage classRosters={data.classRosters} />}
        {(section === 'students' ||
          section === 'classrooms' ||
          section === 'alerts' ||
          section === 'reports' ||
          section === 'settings') && <ComingSoon section={section} />}
      </main>
    </div>
  );
}

function Sidebar({
  flaggedNow,
  section,
  onSelect,
}: {
  flaggedNow: number;
  section: SectionKey;
  onSelect: (s: SectionKey) => void;
}) {
  const items: {
    key: SectionKey;
    icon: string;
    label: string;
    badge?: number;
    badgeColor?: string;
  }[] = [
    { key: 'overview', icon: '📊', label: 'Overview' },
    {
      key: 'live_rosters',
      icon: '📋',
      label: 'Live Rosters',
      badge: flaggedNow,
      badgeColor: 'bg-[#ba1a1a]',
    },
    { key: 'attendance', icon: '📝', label: 'Attendance' },
    { key: 'students', icon: '👥', label: 'Students' },
    { key: 'classrooms', icon: '🏫', label: 'Classrooms' },
    {
      key: 'alerts',
      icon: '🚨',
      label: 'Alerts',
      badge: flaggedNow,
      badgeColor: 'bg-[#ba1a1a]',
    },
    { key: 'reports', icon: '📈', label: 'Reports' },
    { key: 'settings', icon: '⚙️', label: 'Settings' },
  ];

  return (
    <aside className="w-60 bg-[#171d1e] text-white min-h-screen p-5">
      <div className="flex items-center gap-2 mb-8">
        <div className="w-8 h-8 rounded-lg bg-[#00818a] flex items-center justify-center font-bold font-['Lexend',sans-serif]">
          H
        </div>
        <div className="font-['Lexend',sans-serif] font-semibold">HallPass Pro</div>
      </div>
      <nav className="space-y-1 text-sm">
        {items.map((item) => {
          const active = item.key === section;
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => onSelect(item.key)}
              className={
                active
                  ? 'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#00666e]/30 text-white font-medium border-l-2 border-[#63d7e2] text-left'
                  : 'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-[#bcc9ca] hover:bg-white/5 text-left'
              }
            >
              <span>{item.icon}</span>
              {item.label}
              {item.badge !== undefined && item.badge > 0 && (
                <span
                  className={`ml-auto ${item.badgeColor ?? 'bg-[#00818a]'} text-white text-xs px-2 py-0.5 rounded-full font-['Lexend',sans-serif] font-bold`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>
      <div className="mt-8 pt-5 border-t border-white/10">
        <div className="text-xs text-[#6d797b] uppercase font-semibold mb-2">System</div>
        <div className="text-sm flex items-center gap-2 mb-1.5">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          API live
        </div>
        <div className="text-sm flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          14 kiosks online
        </div>
      </div>
    </aside>
  );
}

function TopBar({
  range,
  setRange,
  section,
  showRangeFilter,
}: {
  range: DateRange;
  setRange: (r: DateRange) => void;
  section: SectionKey;
  showRangeFilter: boolean;
}) {
  const ranges: DateRange[] = ['today', 'week', 'month'];
  const label = (r: DateRange) => r.charAt(0).toUpperCase() + r.slice(1);

  return (
    <div className="bg-white rounded-xl px-6 py-4 mb-5 flex items-center justify-between shadow-sm">
      <div>
        <h1 className="font-['Lexend',sans-serif] text-lg font-semibold">
          Lincoln High · {SECTION_TITLES[section]}
        </h1>
        <div className="text-xs text-[#6d797b]">
          Tuesday, May 12 · 10:42 AM · Period 3 in session
        </div>
      </div>
      {showRangeFilter && (
        <div className="flex gap-2 text-sm">
          {ranges.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => setRange(r)}
              className={
                range === r
                  ? 'px-3 py-1.5 rounded-lg bg-[#eff5f5] text-[#3d494a] font-medium'
                  : 'px-3 py-1.5 rounded-lg text-[#6d797b] hover:bg-[#eff5f5]/50'
              }
            >
              {label(r)}
            </button>
          ))}
          <button
            type="button"
            onClick={() => alert(`Export ${range} report (stub)`)}
            className="px-3 py-1.5 rounded-lg bg-[#00666e] text-white font-medium hover:bg-[#00818a]"
          >
            Export
          </button>
        </div>
      )}
    </div>
  );
}

function KpiStrip({ kpis }: { kpis: Kpis }) {
  const tiles = [
    { label: 'Out Now', value: String(kpis.outNow) },
    { label: kpis.totalLabel, value: String(kpis.total) },
    {
      label: 'Active Flags',
      value: String(kpis.activeFlags),
      red: kpis.activeFlags > 0,
    },
    { label: 'Avg Duration', value: formatElapsed(kpis.avgDurationSeconds) },
    { label: 'Adoption', value: `${kpis.adoptionPct}%` },
    { label: 'Lockdowns', value: String(kpis.lockdowns) },
  ];

  return (
    <div className="grid grid-cols-6 gap-3 mb-5">
      {tiles.map((t) => (
        <div key={t.label} className="bg-white rounded-xl p-4 shadow-sm">
          <div className="text-[10px] uppercase tracking-wide text-[#6d797b] font-semibold">
            {t.label}
          </div>
          <div
            className={
              t.red
                ? "font-['Lexend',sans-serif] font-bold tracking-tight text-2xl mt-1 text-[#ba1a1a]"
                : "font-['Lexend',sans-serif] font-bold tracking-tight text-2xl mt-1"
            }
          >
            {t.value}
          </div>
        </div>
      ))}
    </div>
  );
}

const PREVIEW_LIMIT = 6;

function LiveActivityCard({
  passes,
  now,
  onViewAll,
}: {
  passes: ActivePass[];
  now: number;
  onViewAll: () => void;
}) {
  const sorted = useMemo(
    () =>
      [...passes].sort(
        (a, b) =>
          elapsedSec(b.startedAt, now) - elapsedSec(a.startedAt, now),
      ),
    [passes, now],
  );
  const preview = sorted.slice(0, PREVIEW_LIMIT);
  const hidden = passes.length - preview.length;

  return (
    <div className="col-span-7 bg-white rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-['Lexend',sans-serif] font-semibold text-base">Live activity</h3>
        <span className="text-xs text-[#00666e] flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00818a] animate-pulse" />
          Streaming · {passes.length} out
        </span>
      </div>
      <div className="space-y-2.5 text-sm">
        {preview.map((pass) => {
          const elapsed = elapsedSec(pass.startedAt, now);
          const flagged = elapsed > pass.thresholdSeconds;
          return (
            <button
              key={pass.id}
              type="button"
              onClick={onViewAll}
              className={
                flagged
                  ? 'w-full flex items-center justify-between px-3 py-2 rounded-lg bg-[#ffdad6]/40 text-left hover:bg-[#ffdad6]/60 transition-colors'
                  : 'w-full flex items-center justify-between px-3 py-2 rounded-lg bg-[#eff5f5] text-left hover:bg-[#eff5f5]/70 transition-colors'
              }
            >
              <div>
                <span className="font-semibold">{pass.studentName}</span> · {pass.destination} ·{' '}
                {pass.classroom}
              </div>
              <div
                className={
                  flagged
                    ? "font-['Lexend',sans-serif] font-bold tracking-tight text-[#ba1a1a]"
                    : "font-['Lexend',sans-serif] font-bold tracking-tight text-[#3d494a]"
                }
              >
                {formatElapsed(elapsed)}
                {flagged ? ' ⚠' : ''}
              </div>
            </button>
          );
        })}
      </div>
      <button
        type="button"
        onClick={onViewAll}
        className="mt-4 w-full text-center text-sm font-medium text-[#00666e] hover:text-[#00818a] py-2 rounded-lg hover:bg-[#eff5f5] transition-colors"
      >
        {hidden > 0 ? `View all ${passes.length} active passes →` : 'View full activity log →'}
      </button>
    </div>
  );
}

function ClassroomVolumeCard({
  volume,
  range,
}: {
  volume: ClassroomVolume[];
  range: DateRange;
}) {
  const max = Math.max(...volume.map((c) => c.passCount));
  const colorAt = (i: number) =>
    i <= 1 ? 'bg-[#00666e]' : i <= 3 ? 'bg-[#00818a]' : 'bg-[#63d7e2]';

  const RANGE_LABEL: Record<DateRange, string> = {
    today: 'today',
    week: 'this week',
    month: 'this month',
  };

  return (
    <div className="col-span-5 bg-white rounded-xl p-5 shadow-sm">
      <div className="flex items-end justify-between mb-4">
        <h3 className="font-['Lexend',sans-serif] font-semibold text-base">
          Volume by classroom
        </h3>
        <span className="text-xs text-[#6d797b]">{RANGE_LABEL[range]}</span>
      </div>
      <div className="space-y-3 text-sm">
        {volume.map((c, i) => {
          const lastName = c.teacherName.split(' ').slice(-1)[0];
          const room = c.room.replace('Rm ', '');
          const widthPct = (c.passCount / max) * 100;
          return (
            <div key={c.id}>
              <div className="flex justify-between mb-1">
                <span>
                  {lastName} · {room}
                </span>
                <span className="font-['Lexend',sans-serif] font-bold tracking-tight">
                  {c.passCount}
                </span>
              </div>
              <div className="h-2 bg-[#eff5f5] rounded-full">
                <div
                  className={`h-full rounded-full ${colorAt(i)}`}
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function HourlyChartCard({ range }: { range: DateRange }) {
  const W = 700;
  const H = 180;
  const padX = 30;

  const m = RANGE_MULTIPLIER[range];
  const today = useMemo(() => mockHourlyToday.map((v) => v * m), [m]);
  const avg = useMemo(() => mockHourlyAvg.map((v) => v * m), [m]);

  const max = Math.max(...today, ...avg);
  const xStep = (W - padX * 2) / (today.length - 1);
  const x = (i: number) => padX + i * xStep;
  const y = (v: number) => 30 + (1 - v / max) * (H - 60);
  const todayMax = Math.max(...today);

  const linePath = avg
    .map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(v)}`)
    .join(' ');

  const subtitle =
    range === 'today'
      ? 'Bar: today · Line: 7-day avg'
      : range === 'week'
        ? 'Bar: this week · Line: 7-day avg'
        : 'Bar: this month · Line: 7-day avg';

  return (
    <div className="col-span-8 bg-white rounded-xl p-5 shadow-sm">
      <div className="flex items-end justify-between mb-3">
        <h3 className="font-['Lexend',sans-serif] font-semibold text-base">Movement by hour</h3>
        <span className="text-xs text-[#6d797b]">{subtitle}</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-48">
        <g stroke="#eff5f5" strokeWidth="1">
          <line x1={padX} y1={30} x2={W - padX} y2={30} />
          <line x1={padX} y1={90} x2={W - padX} y2={90} />
          <line x1={padX} y1={150} x2={W - padX} y2={150} />
        </g>
        <g>
          {today.map((v, i) => {
            const barY = y(v);
            const barH = 150 - barY;
            const fill = v === todayMax ? '#00666e' : '#00818a';
            return (
              <rect
                key={i}
                x={x(i) - 18}
                y={barY}
                width={36}
                height={barH}
                fill={fill}
              />
            );
          })}
        </g>
        <path d={linePath} fill="none" stroke="#ba1a1a" strokeWidth="2" strokeDasharray="4,4" />
        <g fontSize="10" fill="#6d797b">
          {hourLabels.map((label, i) => (
            <text key={label} x={x(i) - 8} y={172}>
              {label}
            </text>
          ))}
        </g>
      </svg>
    </div>
  );
}

function FrequentFlyersCard({
  students,
  range,
}: {
  students: TopStudent[];
  range: DateRange;
}) {
  const TITLE: Record<DateRange, string> = {
    today: 'Frequent flyers (today)',
    week: 'Frequent flyers (week)',
    month: 'Frequent flyers (month)',
  };

  return (
    <div className="col-span-4 bg-white rounded-xl p-5 shadow-sm">
      <h3 className="font-['Lexend',sans-serif] font-semibold text-base mb-4">{TITLE[range]}</h3>
      <table className="w-full text-sm">
        <tbody className="divide-y divide-[#eff5f5]">
          {students.map((s) => (
            <tr key={s.id}>
              <td className="py-2 font-semibold">{s.name}</td>
              <td className="py-2 text-right font-['Lexend',sans-serif] font-bold">
                {s.passCount}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LiveActivityFullPage({
  passes,
  now,
  onBack,
}: {
  passes: ActivePass[];
  now: number;
  onBack: () => void;
}) {
  const [filter, setFilter] = useState<OutLocation | 'all' | 'flagged'>('all');

  const filterChips: Array<{ key: typeof filter; label: string }> = [
    { key: 'all', label: `All (${passes.length})` },
    { key: 'flagged', label: 'Flagged ⚠' },
    ...OUT_LOCATIONS.map((l) => ({
      key: l as OutLocation,
      label: `${l} (${passes.filter((p) => p.destination === l).length})`,
    })),
  ];

  const filtered = useMemo(() => {
    const byFilter = passes.filter((p) => {
      if (filter === 'all') return true;
      if (filter === 'flagged') return elapsedSec(p.startedAt, now) > p.thresholdSeconds;
      return p.destination === filter;
    });
    return [...byFilter].sort(
      (a, b) => elapsedSec(b.startedAt, now) - elapsedSec(a.startedAt, now),
    );
  }, [passes, filter, now]);

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="text-sm text-[#00666e] hover:text-[#00818a] font-medium"
          >
            ← Back to Overview
          </button>
          <span className="text-xs text-[#00666e] flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#00818a] animate-pulse" />
            Streaming
          </span>
        </div>
        <div className="text-sm text-[#6d797b]">
          {passes.length} students currently out of class
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-5">
        {filterChips.map((c) => (
          <button
            key={c.key}
            type="button"
            onClick={() => setFilter(c.key)}
            className={
              filter === c.key
                ? 'px-3 py-1.5 rounded-full bg-[#00666e] text-white text-sm font-medium'
                : 'px-3 py-1.5 rounded-full bg-[#eff5f5] text-[#3d494a] text-sm hover:bg-[#eff5f5]/70'
            }
          >
            {c.label}
          </button>
        ))}
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs text-[#6d797b] uppercase font-semibold border-b border-[#eff5f5]">
            <th className="py-2">Student</th>
            <th className="py-2">From</th>
            <th className="py-2">Destination</th>
            <th className="py-2 text-right">Time out</th>
            <th className="py-2 text-right">Threshold</th>
            <th className="py-2 text-right">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[#eff5f5]">
          {filtered.map((p) => {
            const elapsed = elapsedSec(p.startedAt, now);
            const flagged = elapsed > p.thresholdSeconds;
            return (
              <tr key={p.id} className={flagged ? 'bg-[#ffdad6]/30' : ''}>
                <td className="py-2.5 font-semibold">{p.studentName}</td>
                <td className="py-2.5 text-[#3d494a]">{p.classroom}</td>
                <td className="py-2.5">{p.destination}</td>
                <td
                  className={
                    flagged
                      ? "py-2.5 text-right font-['Lexend',sans-serif] font-bold tracking-tight text-[#ba1a1a]"
                      : "py-2.5 text-right font-['Lexend',sans-serif] font-bold tracking-tight text-[#3d494a]"
                  }
                >
                  {formatElapsed(elapsed)}
                </td>
                <td className="py-2.5 text-right text-[#6d797b]">
                  {formatElapsed(p.thresholdSeconds)}
                </td>
                <td className="py-2.5 text-right">
                  {flagged ? (
                    <span className="text-[#ba1a1a] font-semibold">Overdue ⚠</span>
                  ) : (
                    <span className="text-[#00666e]">On time</span>
                  )}
                </td>
              </tr>
            );
          })}
          {filtered.length === 0 && (
            <tr>
              <td colSpan={6} className="py-8 text-center text-[#6d797b] text-sm">
                No passes match this filter.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function LiveRostersPage({
  now,
  classRosters,
  outOfClass,
}: {
  now: number;
  classRosters: ClassRoster[];
  outOfClass: OutOfClassEntry[];
}) {
  const totalStudents = classRosters.reduce((n, c) => n + c.students.length, 0);
  const outCount = outOfClass.length;
  const inClassCount = totalStudents - outCount;

  const byLocation = useMemo(() => {
    const map: Record<OutLocation, OutOfClassEntry[]> = {
      Restroom: [],
      Nurse: [],
      Office: [],
      Hallway: [],
    };
    for (const o of outOfClass) {
      const slot = map[o.destination as OutLocation];
      if (slot) slot.push(o);
    }
    for (const loc of OUT_LOCATIONS) {
      map[loc].sort((a, b) => b.outSinceSeconds - a.outSinceSeconds);
    }
    return map;
  }, [outOfClass]);

  return (
    <div>
      <div className="bg-white border border-[#eff5f5] rounded-xl p-5 mb-5 shadow-sm">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="font-['Lexend',sans-serif] text-xl font-bold mb-1">
              📋 Live Rosters
            </h2>
            <p className="text-sm text-[#3d494a]">
              Confirm every student&apos;s location in real time. Use this for fire drills,
              lockdowns, head counts, or audits. Refreshes every second.
            </p>
          </div>
          <div className="flex gap-3 text-sm">
            <div className="bg-[#eff5f5] rounded-lg px-4 py-2">
              <div className="text-[10px] uppercase text-[#6d797b] font-semibold">Total</div>
              <div className="font-['Lexend',sans-serif] font-bold text-2xl">{totalStudents}</div>
            </div>
            <div className="bg-[#eff5f5] rounded-lg px-4 py-2">
              <div className="text-[10px] uppercase text-[#6d797b] font-semibold">In class</div>
              <div className="font-['Lexend',sans-serif] font-bold text-2xl text-[#00666e]">
                {inClassCount}
              </div>
            </div>
            <div className="bg-[#eff5f5] rounded-lg px-4 py-2">
              <div className="text-[10px] uppercase text-[#6d797b] font-semibold">Out of class</div>
              <div className="font-['Lexend',sans-serif] font-bold text-2xl text-[#ba1a1a]">
                {outCount}
              </div>
            </div>
          </div>
        </div>
      </div>

      <h3 className="font-['Lexend',sans-serif] font-semibold text-base mb-3">
        Out of class — by location
      </h3>
      <div className="grid grid-cols-4 gap-4 mb-6">
        {OUT_LOCATIONS.map((loc) => (
          <LocationBucketCard key={loc} location={loc} entries={byLocation[loc]} now={now} />
        ))}
      </div>

      <h3 className="font-['Lexend',sans-serif] font-semibold text-base mb-3">
        Class rosters
      </h3>
      <div className="grid grid-cols-2 gap-4">
        {classRosters.map((cls) => (
          <ClassRosterCard key={cls.id} cls={cls} />
        ))}
      </div>
    </div>
  );
}

function LocationBucketCard({
  location,
  entries,
  now,
}: {
  location: OutLocation;
  entries: OutOfClassEntry[];
  now: number;
}) {
  const icon: Record<OutLocation, string> = {
    Restroom: '🚻',
    Nurse: '🏥',
    Office: '🏛️',
    Hallway: '🚶',
  };

  return (
    <div className="bg-white rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span>{icon[location]}</span>
          <h4 className="font-['Lexend',sans-serif] font-semibold">{location}</h4>
        </div>
        <span className="bg-[#eff5f5] text-[#3d494a] px-2 py-0.5 rounded-full text-sm font-['Lexend',sans-serif] font-bold">
          {entries.length}
        </span>
      </div>
      {entries.length === 0 ? (
        <div className="text-xs text-[#6d797b] italic">No students here</div>
      ) : (
        <ul className="space-y-2 text-sm">
          {entries.map((e) => {
            const startedAt = new Date(Date.now() - e.outSinceSeconds * 1000).toISOString();
            const elapsed = elapsedSec(startedAt, now);
            const flagged = elapsed > e.thresholdSeconds;
            return (
              <li
                key={e.studentId}
                className={
                  flagged
                    ? 'flex justify-between items-start gap-2 p-2 rounded-lg bg-[#ffdad6]/40'
                    : 'flex justify-between items-start gap-2 p-2 rounded-lg bg-[#eff5f5]'
                }
              >
                <div className="min-w-0">
                  <div className="font-semibold truncate">{e.name}</div>
                  <div className="text-xs text-[#6d797b]">{e.room}</div>
                </div>
                <div
                  className={
                    flagged
                      ? "font-['Lexend',sans-serif] font-bold tracking-tight text-xs text-[#ba1a1a] whitespace-nowrap"
                      : "font-['Lexend',sans-serif] font-bold tracking-tight text-xs text-[#3d494a] whitespace-nowrap"
                  }
                >
                  {formatElapsed(elapsed)}
                  {flagged ? ' ⚠' : ''}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function ClassRosterCard({ cls }: { cls: ClassRoster }) {
  const [expanded, setExpanded] = useState(true);
  const inClass = cls.students.filter((s) => s.location === 'in_class');
  const out = cls.students.filter((s) => s.location !== 'in_class');
  const allAccounted = out.length === 0;

  return (
    <div className="bg-white rounded-xl p-5 shadow-sm">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-start justify-between mb-3 text-left"
      >
        <div>
          <h4 className="font-['Lexend',sans-serif] font-semibold">
            {cls.teacherName} · {cls.room}
          </h4>
          <div className="text-xs text-[#6d797b]">{cls.className}</div>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="text-[#00666e] font-semibold">{inClass.length} in</span>
          <span className="text-[#6d797b]">·</span>
          <span
            className={
              out.length > 0 ? 'text-[#ba1a1a] font-semibold' : 'text-[#6d797b]'
            }
          >
            {out.length} out
          </span>
          {allAccounted && (
            <span className="text-xs bg-[#00666e]/10 text-[#00666e] px-2 py-0.5 rounded-full font-semibold">
              ✓ all accounted
            </span>
          )}
          <span className="text-[#6d797b] text-xs">{expanded ? '▾' : '▸'}</span>
        </div>
      </button>

      {expanded && (
        <>
          {out.length > 0 && (
            <div className="mb-4 border border-[#ffdad6] bg-[#ffdad6]/30 rounded-lg p-3">
              <div className="text-[10px] uppercase tracking-wide text-[#ba1a1a] font-bold mb-2">
                Out of class
              </div>
              <ul className="space-y-1 text-sm">
                {out.map((s) => (
                  <li key={s.id} className="flex justify-between">
                    <span className="font-semibold">{s.name}</span>
                    <span className="text-[#3d494a]">→ {s.location}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <div className="text-[10px] uppercase tracking-wide text-[#6d797b] font-bold mb-2">
              In class ({inClass.length})
            </div>
            <ul className="grid grid-cols-2 gap-x-3 gap-y-1 text-sm">
              {inClass.map((s) => (
                <li key={s.id} className="text-[#3d494a]">
                  {s.name}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </div>
  );
}

type AttendanceStatus = 'present' | 'absent' | 'tardy' | 'excused';

const ATTENDANCE_OPTIONS: { key: AttendanceStatus; label: string; color: string }[] = [
  { key: 'present', label: 'Present', color: '#00666e' },
  { key: 'absent', label: 'Absent', color: '#ba1a1a' },
  { key: 'tardy', label: 'Tardy', color: '#b27800' },
  { key: 'excused', label: 'Excused', color: '#3d494a' },
];

const allPresentMarks = (cls: ClassRoster): Record<string, AttendanceStatus> => {
  const next: Record<string, AttendanceStatus> = {};
  for (const s of cls.students) next[s.id] = 'present';
  return next;
};

function AttendancePage({ classRosters }: { classRosters: ClassRoster[] }) {
  const fallback: ClassRoster = { id: '', className: '', teacherName: '', room: '', students: [] };
  const [classId, setClassId] = useState(classRosters[0]?.id ?? '');
  const [marks, setMarks] = useState<Record<string, AttendanceStatus>>(() =>
    allPresentMarks(classRosters[0] ?? fallback),
  );
  const [submittedAt, setSubmittedAt] = useState<string | null>(null);

  // Re-seed when rosters arrive after mount.
  useEffect(() => {
    if (!classId && classRosters[0]) {
      setClassId(classRosters[0].id);
      setMarks(allPresentMarks(classRosters[0]));
    }
  }, [classRosters, classId]);

  const cls = classRosters.find((c) => c.id === classId) ?? classRosters[0] ?? fallback;

  // Default every student to "present" when the active class changes.
  useEffect(() => {
    setMarks(allPresentMarks(cls));
    setSubmittedAt(null);
  }, [cls]);

  const sortedRoster = useMemo(
    () => [...cls.students].sort((a, b) => a.name.localeCompare(b.name)),
    [cls],
  );

  const counts = useMemo(() => {
    const c = { present: 0, absent: 0, tardy: 0, excused: 0, unmarked: 0 };
    for (const s of sortedRoster) {
      const m = marks[s.id];
      if (m) c[m]++;
      else c.unmarked++;
    }
    return c;
  }, [sortedRoster, marks]);

  const setStatus = (studentId: string, status: AttendanceStatus) => {
    setMarks((prev) => ({ ...prev, [studentId]: status }));
    setSubmittedAt(null);
  };

  const reset = () => {
    setMarks(allPresentMarks(cls));
    setSubmittedAt(null);
  };

  const submit = () => {
    setSubmittedAt(
      new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    );
  };

  return (
    <div>
      {/* Class picker */}
      <div className="bg-white rounded-xl p-4 mb-5 shadow-sm">
        <div className="text-[10px] uppercase tracking-wide text-[#6d797b] font-semibold mb-2">
          Class
        </div>
        <div className="flex flex-wrap gap-2">
          {classRosters.map((c) => {
            const lastName = c.teacherName.split(' ').slice(-1)[0];
            const room = c.room.replace('Rm ', '');
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => setClassId(c.id)}
                className={
                  c.id === classId
                    ? 'px-3 py-2 rounded-lg bg-[#00666e] text-white text-sm font-medium'
                    : 'px-3 py-2 rounded-lg bg-[#eff5f5] text-[#3d494a] text-sm hover:bg-[#eff5f5]/70'
                }
              >
                {lastName} · {room}
              </button>
            );
          })}
        </div>
      </div>

      {/* Class header + bulk actions */}
      <div className="bg-white rounded-xl p-5 mb-5 shadow-sm">
        <div className="flex flex-wrap justify-between items-start gap-4 mb-4">
          <div>
            <h2 className="font-['Lexend',sans-serif] text-lg font-semibold">
              {cls.className}
            </h2>
            <div className="text-sm text-[#6d797b]">
              {cls.teacherName} · {cls.room} · Tuesday, May 12 · Period 3
            </div>
          </div>
          <button
            type="button"
            onClick={reset}
            className="px-3 py-1.5 rounded-lg bg-[#eff5f5] text-[#3d494a] text-sm font-medium hover:bg-[#eff5f5]/70"
          >
            Reset to all present
          </button>
        </div>

        <div className="grid grid-cols-4 gap-2">
          <CountTile label="Present" value={counts.present} color="#00666e" />
          <CountTile label="Absent" value={counts.absent} color="#ba1a1a" />
          <CountTile label="Tardy" value={counts.tardy} color="#b27800" />
          <CountTile label="Excused" value={counts.excused} color="#3d494a" />
        </div>
      </div>

      {/* Roster */}
      <div className="bg-white rounded-xl p-5 mb-5 shadow-sm">
        <ul className="divide-y divide-[#eff5f5]">
          {sortedRoster.map((s) => {
            const m = marks[s.id];
            return (
              <li
                key={s.id}
                className="py-2.5 flex items-center justify-between gap-4"
              >
                <span className="font-semibold text-sm">{s.name}</span>
                <div className="flex gap-1.5 flex-shrink-0">
                  {ATTENDANCE_OPTIONS.map((opt) => {
                    const selected = m === opt.key;
                    return (
                      <button
                        key={opt.key}
                        type="button"
                        onClick={() => setStatus(s.id, opt.key)}
                        className={
                          selected
                            ? 'px-3 py-1.5 rounded-lg text-white text-xs font-medium min-w-[70px]'
                            : 'px-3 py-1.5 rounded-lg bg-[#eff5f5] text-[#3d494a] text-xs hover:bg-[#eff5f5]/70 min-w-[70px]'
                        }
                        style={selected ? { backgroundColor: opt.color } : undefined}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Submit footer */}
      <div className="flex items-center justify-end gap-3">
        {submittedAt && (
          <span className="text-sm text-[#00666e] font-medium">
            ✓ Attendance saved at {submittedAt}
          </span>
        )}
        <button
          type="button"
          onClick={submit}
          className="px-5 py-2 rounded-lg bg-[#00666e] text-white font-medium hover:bg-[#00818a]"
        >
          Submit attendance
        </button>
      </div>
    </div>
  );
}

function CountTile({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="bg-[#eff5f5] rounded-lg px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-[#6d797b] font-semibold">
        {label}
      </div>
      <div
        className="font-['Lexend',sans-serif] font-bold tracking-tight text-xl mt-0.5"
        style={{ color }}
      >
        {value}
      </div>
    </div>
  );
}

function ComingSoon({ section }: { section: SectionKey }) {
  return (
    <div className="bg-white rounded-xl p-12 shadow-sm flex flex-col items-center justify-center text-center min-h-[60vh]">
      <div className="text-5xl mb-4">🚧</div>
      <h2 className="font-['Lexend',sans-serif] text-xl font-semibold mb-2">
        {SECTION_TITLES[section]}
      </h2>
      <p className="text-sm text-[#6d797b] max-w-md">
        This section isn&apos;t built yet. Overview, Live Rosters, and Attendance are the live
        demo surfaces for the hackathon — pick another tab to come back.
      </p>
    </div>
  );
}


function VoiceCallsCard({ calls }: { calls: VoiceCallSummaryApi[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [transcript, setTranscript] = useState<TranscriptTurnApi[]>([]);
  const [loadingId, setLoadingId] = useState<string | null>(null);

  const toggle = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null);
      setTranscript([]);
      return;
    }
    setExpandedId(id);
    setLoadingId(id);
    try {
      const detail = await getVoiceCall(id);
      setTranscript(detail.transcript ?? []);
    } catch {
      setTranscript([]);
    } finally {
      setLoadingId(null);
    }
  };

  const recent = calls.slice(0, 5);

  return (
    <div className="col-span-12 bg-white border border-[#eff5f5] rounded-xl p-5 shadow-sm">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="font-['Lexend',sans-serif] font-semibold text-base">
          📞 Recent Guardian Calls
        </h3>
        <span className="text-xs text-[#6d797b]">
          {calls.length} total · live updates from voice agent
        </span>
      </div>
      {recent.length === 0 ? (
        <p className="text-sm text-[#6d797b]">
          No voice-agent conversations yet. Start one in the outbound voice agent and it will land
          here within a second.
        </p>
      ) : (
        <ul className="divide-y divide-[#eff5f5]">
          {recent.map((c) => {
            const open = expandedId === c.id;
            return (
              <li key={c.id} className="py-3">
                <button
                  type="button"
                  onClick={() => void toggle(c.id)}
                  className="w-full text-left flex items-start gap-3 hover:bg-[#f7f9f9] p-2 rounded-lg transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-semibold text-sm">{c.studentName}</span>
                      <span className="text-[10px] uppercase tracking-wide bg-[#eff5f5] text-[#3d494a] px-1.5 py-0.5 rounded">
                        {c.scenario}
                      </span>
                      {c.parentConfirmed === true && (
                        <span className="text-[10px] uppercase tracking-wide bg-[#dff5f6] text-[#00666e] px-1.5 py-0.5 rounded">
                          confirmed
                        </span>
                      )}
                      {c.alertId && (
                        <span className="text-[10px] uppercase tracking-wide bg-[#fef3e2] text-[#b27800] px-1.5 py-0.5 rounded">
                          alert-driven
                        </span>
                      )}
                    </div>
                    {c.excuseSummary && (
                      <p className="text-sm text-[#3d494a] truncate">{c.excuseSummary}</p>
                    )}
                    <p className="text-xs text-[#6d797b] mt-0.5">
                      {new Date(c.callEndedAt).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                      {c.language && ` · ${c.language}`}
                    </p>
                  </div>
                  <span className="text-xs text-[#6d797b] mt-2 select-none">{open ? '▾' : '▸'}</span>
                </button>
                {open && (
                  <div className="mt-2 ml-2 pl-3 border-l-2 border-[#eff5f5]">
                    {loadingId === c.id ? (
                      <p className="text-xs text-[#6d797b] py-2">Loading transcript…</p>
                    ) : transcript.length === 0 ? (
                      <p className="text-xs text-[#6d797b] py-2">
                        Voice agent didn&apos;t persist a transcript for this call.
                      </p>
                    ) : (
                      <ul className="space-y-1.5 py-2">
                        {transcript.map((t, i) => (
                          <li key={i} className="text-sm">
                            <span
                              className={`inline-block min-w-[70px] mr-2 text-[10px] uppercase font-bold tracking-wide ${
                                t.speaker === 'agent' ? 'text-[#00666e]' : 'text-[#3d494a]'
                              }`}
                            >
                              {t.speaker}
                            </span>
                            <span className="text-[#171d1e]">{t.text}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
