import { useState, useEffect } from 'react';
import { Bath, Stethoscope, Building2, Footprints, DoorOpen, LogIn } from 'lucide-react';
import type { Destination, HallPass } from '../types';
import { ApiError, returnHallPass } from '../api/client';

interface CheckedOutCardProps {
  pass: HallPass;
  onChange?: () => void;
}

function getDestinationIcon(destination: Destination) {
  switch (destination) {
    case 'RESTROOM':
      return <Bath size={16} />;
    case 'NURSE':
      return <Stethoscope size={16} />;
    case 'OFFICE':
      return <Building2 size={16} />;
    case 'HALLWAY':
      return <Footprints size={16} />;
    case 'CLASSROOM':
      return <DoorOpen size={16} />;
    default:
      return <Building2 size={16} />;
  }
}

function formatElapsed(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  return `${minutes}m`;
}

export function CheckedOutCard({ pass, onChange }: CheckedOutCardProps) {
  const [elapsed, setElapsed] = useState(() => Date.now() - pass.checkedOutAt.getTime());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isOverdue = elapsed > 15 * 60 * 1000;

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Date.now() - pass.checkedOutAt.getTime());
    }, 1000);
    return () => clearInterval(interval);
  }, [pass.checkedOutAt]);

  const handleCheckIn = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await returnHallPass(pass.id);
      onChange?.();
    } catch (e) {
      const msg =
        e instanceof ApiError ? `${e.status} ${e.message}` : (e as Error).message;
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className={`bg-white rounded-lg shadow-sm border-2 p-4 min-w-[200px] flex flex-col gap-3 ${
        isOverdue ? 'border-red-400' : 'border-gray-100'
      }`}
    >
      {isOverdue && (
        <span className="text-xs font-bold text-emergency uppercase tracking-wide">
          OVERDUE
        </span>
      )}
      <div>
        <p className="font-bold text-gray-900 text-base">{pass.studentName}</p>
        <div className="flex items-center gap-1 mt-1 text-primary font-semibold text-sm">
          {getDestinationIcon(pass.destination)}
          <span>{pass.destination}</span>
        </div>
      </div>

      <div
        className={`text-3xl font-sans font-bold tabular-nums ${
          isOverdue ? 'text-emergency' : 'text-gray-800'
        }`}
      >
        {formatElapsed(elapsed)}
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <button
        onClick={handleCheckIn}
        disabled={submitting}
        className="mt-auto flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-primary active:bg-gray-300 disabled:opacity-50"
      >
        <LogIn size={14} />
        {submitting ? 'Checking in…' : 'Tap to Check-in'}
      </button>
    </div>
  );
}
