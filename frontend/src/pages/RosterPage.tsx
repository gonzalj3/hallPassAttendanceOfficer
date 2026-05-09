import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Settings, Clock, Users, UserCheck } from 'lucide-react';
import { useApp } from '../context/AppContext';
import { CheckedOutCard } from '../components/CheckedOutCard';
import { ApiError, getRoster, hydrateActivePasses } from '../api/client';
import { useRealtime } from '../api/realtime';
import type { RosterApi, StudentApi } from '../api/types';
import type { HallPass } from '../types';

export function RosterPage() {
  const navigate = useNavigate();
  const { sessionId } = useParams<{ sessionId: string }>();
  const { setSelectedSession, setSelectedStudent } = useApp();

  const [roster, setRoster] = useState<RosterApi | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [guestName, setGuestName] = useState('');

  const fetchRoster = useCallback(async () => {
    if (!sessionId) return;
    try {
      const data = await getRoster(sessionId);
      setRoster(data);
      setSelectedSession(data.session);
      setError(null);
    } catch (e: unknown) {
      const msg = e instanceof ApiError ? `${e.status} ${e.message}` : (e as Error).message;
      setError(`Failed to load roster: ${msg}`);
    }
  }, [sessionId, setSelectedSession]);

  useEffect(() => {
    fetchRoster();
  }, [fetchRoster]);

  // Subscribe to realtime events for this class. Any hall-pass / alert
  // event triggers a refetch so the UI stays consistent with the server.
  // We listen at school scope too so alerts for this class's students
  // (e.g. the 15-min restroom alert from Phase 6) surface here as well.
  const channels = useMemo(() => {
    if (!roster) return [];
    return [`class:${roster.session.classId}`, `school:${roster.session.schoolId}`];
  }, [roster]);

  useRealtime({
    channels,
    onEvent: (envelope) => {
      const name = envelope.event?.event;
      if (
        name === 'hallpass.issued' ||
        name === 'hallpass.returned' ||
        name === 'hallpass.overdue' ||
        name === 'alert.raised'
      ) {
        fetchRoster();
      }
    },
  });

  const activePasses: HallPass[] = useMemo(
    () => (roster ? hydrateActivePasses(roster) : []),
    [roster]
  );
  const inClassStudents: StudentApi[] = useMemo(() => {
    if (!roster) return [];
    const checkedOutIds = new Set(activePasses.map((p) => p.studentId));
    return roster.students.filter((s) => !checkedOutIds.has(s.id));
  }, [roster, activePasses]);
  const inClassCount = inClassStudents.length;

  const handleStudentTap = (student: StudentApi) => {
    setSelectedStudent(student);
    navigate(`/destination/${student.id}`);
  };

  const handleGuestCheckIn = (e: React.FormEvent) => {
    e.preventDefault();
    if (guestName.trim()) {
      setGuestName('');
    }
  };

  const session = roster?.session;

  return (
    <div className="min-h-screen font-sans" style={{ backgroundColor: '#f0f0ea' }}>
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <button
            onClick={() => navigate('/classes')}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 min-h-[44px] px-1 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300 transition-colors"
          >
            <ArrowLeft size={20} />
            <span className="font-medium text-sm">Classes</span>
          </button>
          <button className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300">
            <Settings size={20} />
          </button>
        </div>
      </header>

      {/* Session Info Bar */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-gray-900">
              {session ? `${session.period}: ${session.name}` : 'Loading roster…'}
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              {session
                ? `${inClassCount + activePasses.length} Students • Room ${session.room}`
                : ''}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 text-sm font-semibold rounded-full">
              <UserCheck size={14} />
              {inClassCount} In Class
            </span>
            <span
              className="flex items-center gap-1.5 px-3 py-1.5 text-white text-sm font-semibold rounded-full"
              style={{ backgroundColor: '#079da8' }}
            >
              <Clock size={14} />
              {activePasses.length} Checked Out
            </span>
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-6 pb-28 space-y-8">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {error}
          </div>
        )}

        {/* Checked Out Section */}
        {activePasses.length > 0 && (
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Clock size={18} style={{ color: '#079da8' }} />
              <h2 className="text-sm font-bold uppercase tracking-widest text-gray-600">
                Checked Out
              </h2>
            </div>
            <div className="flex flex-wrap gap-4">
              {activePasses.map((pass) => (
                <CheckedOutCard key={pass.id} pass={pass} onChange={fetchRoster} />
              ))}
            </div>
          </section>
        )}

        {/* In Class Section */}
        <section>
          <div className="flex items-center gap-2 mb-4">
            <Users size={18} className="text-gray-500" />
            <h2 className="text-sm font-bold uppercase tracking-widest text-gray-600">
              In Class
            </h2>
          </div>
          <div className="flex flex-wrap gap-2">
            {inClassStudents.map((student) => (
              <button
                key={student.id}
                onClick={() => handleStudentTap(student)}
                className="px-4 py-2.5 bg-white border border-gray-200 rounded-lg text-sm font-medium text-gray-800 hover:border-primary hover:shadow-sm min-h-[44px] transition-all focus:outline-none focus:ring-2 active:scale-95"
                style={{ ['--tw-ring-color' as string]: '#079da8' } as React.CSSProperties}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#079da8';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '';
                }}
              >
                {student.name}
              </button>
            ))}
            {!roster && !error && (
              <span className="text-sm text-gray-400">Loading students…</span>
            )}
          </div>
        </section>

        {/* Guest Check-In */}
        <section>
          <h2 className="text-sm font-bold uppercase tracking-widest text-gray-600 mb-3">
            Guest Check-In
          </h2>
          <form onSubmit={handleGuestCheckIn} className="flex gap-2 max-w-md">
            <input
              type="text"
              value={guestName}
              onChange={(e) => setGuestName(e.target.value)}
              placeholder="Student Name or ID..."
              className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg text-sm text-gray-900 placeholder-gray-400 focus:outline-none min-h-[44px]"
              onFocus={(e) => {
                e.currentTarget.style.borderColor = '#079da8';
                e.currentTarget.style.boxShadow = '0 0 0 2px rgba(7,157,168,0.15)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = '';
                e.currentTarget.style.boxShadow = '';
              }}
            />
            <button
              type="submit"
              className="px-5 py-2.5 text-white font-semibold rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 active:opacity-90 whitespace-nowrap"
              style={{ backgroundColor: '#079da8' }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#068090')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#079da8')}
            >
              Check In
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
