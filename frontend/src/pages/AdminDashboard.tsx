import { useEffect, useState } from 'react';
import {
  mockKpis,
  mockActivePasses,
  mockTopStudents,
  mockClassroomVolume,
  mockCapacity,
  mockHourlyToday,
  mockHourlyAvg,
  hourLabels,
  type ActivePass,
} from '../data/mockAdmin';

type DateRange = 'today' | 'week' | 'month';

const formatElapsed = (s: number) =>
  `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

const elapsedSec = (iso: string, now: number) =>
  Math.max(0, Math.floor((now - new Date(iso).getTime()) / 1000));

export default function AdminDashboard() {
  const [range, setRange] = useState<DateRange>('today');
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen bg-[#e9eff0] flex font-['Atkinson_Hyperlegible_Next',sans-serif] text-[#171d1e]">
      <Sidebar />
      <main className="flex-1 p-6">
        <TopBar range={range} setRange={setRange} />
        <KpiStrip />
        <div className="grid grid-cols-12 gap-5">
          <LiveActivityCard passes={mockActivePasses} now={now} />
          <ClassroomVolumeCard />
          <CapacityCard />
          <HourlyChartCard />
          <FrequentFlyersCard />
        </div>
      </main>
    </div>
  );
}

function Sidebar() {
  const navItems = [
    { label: 'Overview', emoji: '📊', active: true },
    { label: 'Live Rosters', emoji: '📋', active: false },
    { label: 'Attendance', emoji: '📝', active: false },
    { label: 'Alerts', emoji: '🚨', active: false, badge: mockKpis.activeFlags },
    { label: 'Reports', emoji: '📈', active: false },
    { label: 'Settings', emoji: '⚙️', active: false },
  ];

  return (
    <aside className="w-60 min-h-screen bg-[#171d1e] p-6 text-white flex flex-col justify-between">
      <div>
        <div className="mb-10">
          <div className="text-sm uppercase tracking-[0.22em] text-[#63d7e2]">HallPass Pro</div>
          <div className="mt-4 text-2xl font-['Lexend',sans-serif] font-semibold">Operations</div>
        </div>

        <nav className="space-y-2">
          {navItems.map((item) => (
            <div
              key={item.label}
              className={`flex items-center justify-between rounded-2xl px-4 py-3 text-sm ${
                item.active
                  ? 'bg-[#00666e]/30 text-white font-medium border-l-2 border-[#63d7e2]'
                  : 'text-[#bcc9ca] hover:bg-white/5'
              }`}
            >
              <span className="flex items-center gap-3">
                <span>{item.emoji}</span>
                <span>{item.label}</span>
              </span>
              {item.badge ? (
                <span className="rounded-full bg-[#ba1a1a] px-2 py-0.5 text-[11px] font-semibold text-white">
                  {item.badge}
                </span>
              ) : null}
            </div>
          ))}
        </nav>
      </div>

      <div className="space-y-4">
        <div className="text-xs uppercase tracking-[0.24em] text-[#4fb8c6]">System</div>
        <div className="space-y-3">
          <div className="flex items-center gap-3 rounded-2xl bg-[#0f1d22] px-4 py-3">
            <span className="h-2.5 w-2.5 rounded-full bg-[#3fd3e5] animate-pulse" />
            <span className="text-sm text-[#bcc9ca]">API live</span>
          </div>
          <div className="flex items-center gap-3 rounded-2xl bg-[#0f1d22] px-4 py-3">
            <span className="h-2.5 w-2.5 rounded-full bg-[#3fd3e5] animate-pulse" />
            <span className="text-sm text-[#bcc9ca]">14 kiosks online</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

function TopBar({
  range,
  setRange,
}: {
  range: DateRange;
  setRange: (range: DateRange) => void;
}) {
  const options: DateRange[] = ['today', 'week', 'month'];

  return (
    <div className="mb-5 rounded-xl bg-white p-5 shadow-sm flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
      <div>
        <div className="text-lg font-['Lexend',sans-serif] font-semibold">Lincoln High · Operations Overview</div>
        <div className="mt-2 text-sm text-[#6d797b]">Tuesday, May 12 · 10:42 AM · Period 3 in session</div>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setRange(option)}
            className={`rounded-full px-4 py-2 text-sm ${
              range === option
                ? 'bg-[#eff5f5] text-[#3d494a] font-medium'
                : 'text-[#6d797b]'
            }`}
          >
            {option === 'today' ? 'Today' : option === 'week' ? 'Week' : 'Month'}
          </button>
        ))}
        <button type="button" className="rounded-full bg-[#00666e] px-4 py-2 text-sm font-medium text-white">
          Export
        </button>
      </div>
    </div>
  );
}

function KpiStrip() {
  return (
    <div className="grid grid-cols-5 gap-3 mb-5">
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="text-[10px] uppercase tracking-[0.22em] text-[#6d797b]">Absent</div>
        <div className="mt-3 text-2xl font-['Lexend',sans-serif] font-bold">{mockKpis.absent}</div>
      </div>
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="text-[10px] uppercase tracking-[0.22em] text-[#6d797b]">Out Now</div>
        <div className="mt-3 text-2xl font-['Lexend',sans-serif] font-bold">{mockKpis.outNow}</div>
      </div>
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="text-[10px] uppercase tracking-[0.22em] text-[#6d797b]">Today Total</div>
        <div className="mt-3 text-2xl font-['Lexend',sans-serif] font-bold">{mockKpis.todayTotal}</div>
      </div>
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="text-[10px] uppercase tracking-[0.22em] text-[#6d797b]">Active Flags</div>
        <div className={`mt-3 text-2xl font-['Lexend',sans-serif] font-bold ${mockKpis.activeFlags > 0 ? 'text-[#ba1a1a]' : 'text-[#171d1e]'}`}>
          {mockKpis.activeFlags}
        </div>
      </div>
      <div className="rounded-xl bg-white p-4 shadow-sm">
        <div className="text-[10px] uppercase tracking-[0.22em] text-[#6d797b]">Avg Duration</div>
        <div className="mt-3 text-2xl font-['Lexend',sans-serif] font-bold">{formatElapsed(mockKpis.avgDurationSeconds)}</div>
      </div>
    </div>
  );
}

function LiveActivityCard({ passes, now }: { passes: ActivePass[]; now: number }) {
  return (
    <section className="col-span-5 rounded-xl bg-white p-5 shadow-sm">
      <div className="mb-5 flex items-center justify-between">
        <div className="text-lg font-['Lexend',sans-serif] font-semibold">Live activity</div>
        <div className="flex items-center gap-2 rounded-full border border-[#e4f3f5] bg-[#f3f7f8] px-3 py-1 text-sm text-[#3d494a]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#00818a] animate-pulse" />
          Streaming
        </div>
      </div>
      <div className="space-y-3">
        {passes.map((pass) => {
          const elapsed = elapsedSec(pass.startedAt, now);
          const flagged = elapsed > pass.thresholdSeconds;
          return (
            <div
              key={pass.id}
              className={`rounded-xl px-3 py-3 ${flagged ? 'bg-[#ffdad6]/40' : 'bg-[#eff5f5]'}`}
            >
              <div className="flex items-center justify-between gap-4 text-sm">
                <div className="text-sm text-[#3d494a]">
                  <span className="font-semibold text-[#171d1e]">{pass.studentName}</span>{' '}
                  · {pass.destination} · {pass.classroom}
                </div>
                <div className={`font-['Lexend',sans-serif] font-bold text-sm ${flagged ? 'text-[#ba1a1a]' : 'text-[#3d494a]'}`}>
                  {formatElapsed(elapsed)}{flagged ? ' ⚠' : ''}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ClassroomVolumeCard() {
  const maxCount = Math.max(...mockClassroomVolume.map((item) => item.passCount));

  return (
    <section className="col-span-4 rounded-xl bg-white p-5 shadow-sm">
      <div className="mb-5 text-lg font-['Lexend',sans-serif] font-semibold">Volume by classroom</div>
      <div className="space-y-4">
        {mockClassroomVolume.map((item, index) => {
          const lastName = item.teacherName.split(' ').slice(-1)[0];
          const barWidth = `${Math.round((item.passCount / maxCount) * 100)}%`;
          const fillClass = index <= 1 ? 'bg-[#00666e]' : index <= 3 ? 'bg-[#00818a]' : 'bg-[#63d7e2]';
          return (
            <div key={item.id} className="space-y-2">
              <div className="flex items-center justify-between text-sm text-[#3d494a]">
                <span>{lastName} · {item.room.replace('Rm ', '')}</span>
                <span className="font-['Lexend',sans-serif] font-bold">{item.passCount}</span>
              </div>
              <div className="h-2 rounded-full bg-[#eff5f5]">
                <div className={`h-2 rounded-full ${fillClass}`} style={{ width: barWidth }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function CapacityCard() {
  return (
    <section className="col-span-3 rounded-xl bg-white p-5 shadow-sm">
      <div className="mb-5 text-lg font-['Lexend',sans-serif] font-semibold">Capacity</div>
      <div className="space-y-3">
        {mockCapacity.map((row) => {
          const isFull = row.status === 'full';
          const isUnlimited = row.status === 'unlimited';
          const valueTextClass = isFull ? 'text-[#ba1a1a]' : isUnlimited ? 'text-[#3d494a]' : 'text-[#00666e]';
          const containerClass = isFull ? 'bg-[#ffdad6]/40 border border-[#ffdad6]' : 'bg-[#eff5f5]';
          return (
            <div key={row.destination} className={`${containerClass} rounded-3xl p-4`}> 
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="font-semibold text-[#171d1e]">{row.destination}</div>
                  <div className="text-sm text-[#6d797b]">{row.status === 'full' ? 'Full' : row.status === 'available' ? 'Available' : 'Unlimited'}</div>
                </div>
                <div className={`text-lg font-['Lexend',sans-serif] font-bold ${valueTextClass}`}>
                  {row.limit === null ? row.current : `${row.current}/${row.limit}`}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function HourlyChartCard() {
  const W = 700;
  const H = 180;
  const padX = 30;
  const maxValue = Math.max(...mockHourlyToday, ...mockHourlyAvg, 1);
  const xStep = (W - padX * 2) / (mockHourlyToday.length - 1);
  const x = (i: number) => padX + i * xStep;
  const y = (value: number) => 30 + (1 - value / maxValue) * (H - 60);

  const avgPath = mockHourlyAvg
    .map((value, index) => `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(value)}`)
    .join(' ');

  const topToday = Math.max(...mockHourlyToday);

  return (
    <section className="col-span-8 rounded-xl bg-white p-5 shadow-sm">
      <div className="mb-3">
        <div className="text-lg font-['Lexend',sans-serif] font-semibold">Movement by hour</div>
        <div className="text-sm text-[#6d797b]">Bar: today · Line: 7-day avg</div>
      </div>
      <div className="overflow-x-auto">
        <svg viewBox="0 0 700 180" className="w-full" aria-hidden="true">
          {[30, 90, 150].map((lineY) => (
            <line key={lineY} x1={padX} y1={lineY} x2={W - padX} y2={lineY} stroke="#eff5f5" strokeWidth="1" />
          ))}

          {mockHourlyToday.map((value, index) => {
            const barX = x(index) - 18;
            const barY = y(value);
            const barHeight = 150 - barY;
            return (
              <rect
                key={`bar-${index}`}
                x={barX}
                y={barY}
                width={36}
                height={barHeight}
                rx={8}
                fill={value === topToday ? '#00666e' : '#00818a'}
              />
            );
          })}

          <path d={avgPath} fill="none" stroke="#ba1a1a" strokeWidth="2" strokeDasharray="4,4" />

          {hourLabels.map((label, index) => (
            <text key={label} x={x(index)} y={172} textAnchor="middle" fontSize="10" fill="#6d797b">
              {label}
            </text>
          ))}
        </svg>
      </div>
    </section>
  );
}

function FrequentFlyersCard() {
  return (
    <section className="col-span-4 rounded-xl bg-white p-5 shadow-sm">
      <div className="mb-5 text-lg font-['Lexend',sans-serif] font-semibold">Frequent flyers (week)</div>
      <table className="w-full text-sm">
        <tbody className="divide-y divide-[#eff5f5]">
          {mockTopStudents.map((student) => (
            <tr key={student.id}>
              <td className="py-2 font-semibold text-[#171d1e]">{student.name}</td>
              <td className="py-2 text-right font-['Lexend',sans-serif] font-bold text-[#171d1e]">{student.passCount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
