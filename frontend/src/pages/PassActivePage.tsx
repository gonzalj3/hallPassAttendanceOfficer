import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle2,
  ArrowLeft,
  Bath,
  Building2,
  Stethoscope,
  Footprints,
  DoorOpen,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import type { Destination } from '../types';

function getDestinationIcon(destination: Destination | null) {
  switch (destination) {
    case 'RESTROOM':
      return <Bath size={28} style={{ color: '#079da8' }} />;
    case 'NURSE':
      return <Stethoscope size={28} style={{ color: '#079da8' }} />;
    case 'OFFICE':
      return <Building2 size={28} style={{ color: '#079da8' }} />;
    case 'HALLWAY':
      return <Footprints size={28} style={{ color: '#079da8' }} />;
    case 'CLASSROOM':
      return <DoorOpen size={28} style={{ color: '#079da8' }} />;
    default:
      return <Building2 size={28} style={{ color: '#079da8' }} />;
  }
}

function getDestinationLabel(destination: Destination | null): string {
  if (!destination) return 'OFFICE';
  return destination;
}

export function PassActivePage() {
  const navigate = useNavigate();
  const {
    selectedStudent,
    selectedDestination,
    selectedSession,
    addHallPass,
    setSelectedStudent,
    setSelectedDestination,
  } = useApp();

  const [started, setStarted] = useState(false);
  const [departureTime] = useState(new Date());
  const hasAddedPass = useRef(false);
  const DURATION_MS = 4000;

  // Add the hall pass once on mount
  useEffect(() => {
    if (!hasAddedPass.current && selectedStudent && selectedDestination) {
      hasAddedPass.current = true;
      const now = new Date();
      addHallPass({
        id: `pass-${Date.now()}`,
        studentId: selectedStudent.id,
        studentName: selectedStudent.name,
        destination: selectedDestination,
        checkedOutAt: now,
        expectedReturnAt: new Date(now.getTime() + 15 * 60 * 1000),
        status: 'ACTIVE',
      });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Trigger CSS transition on next frame so the browser sees 0→100
  useEffect(() => {
    const raf = requestAnimationFrame(() => setStarted(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  // Auto-navigate after 4s
  useEffect(() => {
    const timeout = setTimeout(() => {
      handleReturn();
    }, DURATION_MS);
    return () => clearTimeout(timeout);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleReturn = () => {
    const sessionId = selectedSession?.id ?? 'session-3';
    setSelectedStudent(null);
    setSelectedDestination(null);
    navigate(`/roster/${sessionId}`);
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <div
      className="min-h-screen font-sans flex items-center justify-center p-4"
      style={{
        background: 'linear-gradient(135deg, #f0f0ea 0%, #e8f5f6 50%, #d1ecee 100%)',
      }}
    >
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        {/* Checkmark Icon */}
        <div className="flex justify-center mb-6">
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center"
            style={{ backgroundColor: '#e8f5f6' }}
          >
            <CheckCircle2 size={48} style={{ color: '#079da8' }} />
          </div>
        </div>

        {/* Title */}
        <div className="text-center mb-6">
          <h1 className="text-3xl font-black text-gray-900 mb-2">Pass Active!</h1>
          <p className="text-gray-500">Please check back in when you return.</p>
        </div>

        {/* Info Cards */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {/* Student Card */}
          <div
            className="rounded-xl p-4 border"
            style={{ backgroundColor: '#e8f5f6', borderColor: '#a3d9dd' }}
          >
            <p className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-1.5">
              STUDENT
            </p>
            <p className="font-bold text-gray-900 text-sm leading-snug">
              {selectedStudent?.name ?? 'Student Name'}
            </p>
          </div>

          {/* Destination Card */}
          <div
            className="rounded-xl p-4 border"
            style={{ backgroundColor: '#e8f5f6', borderColor: '#a3d9dd' }}
          >
            <p className="text-xs font-bold uppercase tracking-widest text-gray-500 mb-1.5">
              TO: {getDestinationLabel(selectedDestination)}
            </p>
            <div className="flex items-center gap-2">
              {getDestinationIcon(selectedDestination)}
              <div>
                <p className="font-bold text-gray-900 text-sm">{formatTime(departureTime)}</p>
                <p className="text-xs text-gray-500">Departure</p>
              </div>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mb-3">
          <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: started ? '100%' : '0%',
                backgroundColor: '#079da8',
                transition: `width ${DURATION_MS}ms linear`,
              }}
            />
          </div>
        </div>

        <p className="text-center text-sm text-gray-400 mb-5">Returning to Roster...</p>

        {/* Return Button */}
        <button
          onClick={handleReturn}
          className="w-full flex items-center justify-center gap-2 py-3 text-white font-semibold rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 active:opacity-90"
          style={{ backgroundColor: '#079da8' }}
          onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#068090')}
          onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#079da8')}
        >
          <ArrowLeft size={18} />
          Return Now
        </button>
      </div>
    </div>
  );
}
