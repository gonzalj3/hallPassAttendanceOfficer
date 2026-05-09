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
  AlertCircle,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import type { Destination, HallPass } from '../types';
import { ApiError, issueHallPass } from '../api/client';

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
    setSelectedStudent,
    setSelectedDestination,
  } = useApp();

  const [pass, setPass] = useState<HallPass | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const hasIssued = useRef(false);
  const DURATION_MS = 4000;

  // Issue the pass exactly once on mount.
  useEffect(() => {
    if (hasIssued.current) return;
    if (!selectedStudent || !selectedDestination || !selectedSession) {
      navigate('/classes', { replace: true });
      return;
    }
    hasIssued.current = true;

    issueHallPass({
      studentId: selectedStudent.id,
      sessionId: selectedSession.id,
      destination: selectedDestination,
    })
      .then((p) => {
        setPass(p);
      })
      .catch((e: unknown) => {
        const msg =
          e instanceof ApiError ? `${e.status} ${e.message}` : (e as Error).message;
        setError(msg);
      });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Trigger the CSS transition on the next frame so the browser observes
  // a 0% → 100% change with the transition rule attached. Single rAF +
  // a single timer beats a 50ms interval recomputing width in JS.
  useEffect(() => {
    if (!pass) return;
    const raf = requestAnimationFrame(() => setStarted(true));
    const timeout = setTimeout(() => handleReturn(), DURATION_MS);
    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timeout);
    };
  }, [pass]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleReturn = () => {
    const sessionId = selectedSession?.id;
    setSelectedStudent(null);
    setSelectedDestination(null);
    if (sessionId) navigate(`/roster/${sessionId}`);
    else navigate('/classes');
  };

  const formatTime = (date: Date) =>
    date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });

  if (error) {
    return (
      <div
        className="min-h-screen font-sans flex items-center justify-center p-4"
        style={{ background: '#f0f0ea' }}
      >
        <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
          <div className="flex justify-center mb-6">
            <div className="w-20 h-20 rounded-full bg-red-50 flex items-center justify-center">
              <AlertCircle size={48} className="text-red-600" />
            </div>
          </div>
          <h1 className="text-2xl font-black text-gray-900 mb-2 text-center">
            Couldn't issue pass
          </h1>
          <p className="text-gray-600 text-sm text-center mb-6">{error}</p>
          <button
            onClick={handleReturn}
            className="w-full flex items-center justify-center gap-2 py-3 text-white font-semibold rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
            style={{ backgroundColor: '#079da8' }}
          >
            <ArrowLeft size={18} />
            Back to Roster
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen font-sans flex items-center justify-center p-4"
      style={{
        background: 'linear-gradient(135deg, #f0f0ea 0%, #e8f5f6 50%, #d1ecee 100%)',
      }}
    >
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="flex justify-center mb-6">
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center"
            style={{ backgroundColor: '#e8f5f6' }}
          >
            <CheckCircle2 size={48} style={{ color: '#079da8' }} />
          </div>
        </div>

        <div className="text-center mb-6">
          <h1 className="text-3xl font-black text-gray-900 mb-2">
            {pass ? 'Pass Active!' : 'Issuing pass…'}
          </h1>
          <p className="text-gray-500">
            {pass ? 'Please check back in when you return.' : ''}
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3 mb-6">
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
                <p className="font-bold text-gray-900 text-sm">
                  {pass ? formatTime(pass.checkedOutAt) : '—'}
                </p>
                <p className="text-xs text-gray-500">Departure</p>
              </div>
            </div>
          </div>
        </div>

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

        <p className="text-center text-sm text-gray-400 mb-5">
          {pass ? 'Returning to Roster…' : 'Talking to backend…'}
        </p>

        <button
          onClick={handleReturn}
          className="w-full flex items-center justify-center gap-2 py-3 text-white font-semibold rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 active:opacity-90"
          style={{ backgroundColor: '#079da8' }}
        >
          <ArrowLeft size={18} />
          Return Now
        </button>
      </div>
    </div>
  );
}
