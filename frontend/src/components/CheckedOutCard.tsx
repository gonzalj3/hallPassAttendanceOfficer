import { useState, useEffect } from 'react';
import { Bath, Stethoscope, Building2, Footprints, DoorOpen, LogIn } from 'lucide-react';
import type { HallPass, Destination } from '../types';
import { useApp } from '../context/AppContext';

interface CheckedOutCardProps {
  pass: HallPass;
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

function getDestinationLabel(destination: Destination): string {
  switch (destination) {
    case 'RESTROOM':
      return 'RESTROOM';
    case 'NURSE':
      return 'NURSE';
    case 'OFFICE':
      return 'OFFICE';
    case 'HALLWAY':
      return 'HALLWAY';
    case 'CLASSROOM':
      return 'CLASSROOM';
    default:
      return destination;
  }
}

function formatElapsed(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  return `${minutes}m`;
}

export function CheckedOutCard({ pass }: CheckedOutCardProps) {
  const { returnHallPass } = useApp();
  const [elapsed, setElapsed] = useState(() => Date.now() - pass.checkedOutAt.getTime());
  const isOverdue = elapsed > 15 * 60 * 1000;

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed(Date.now() - pass.checkedOutAt.getTime());
    }, 1000);
    return () => clearInterval(interval);
  }, [pass.checkedOutAt]);

  const handleCheckIn = () => {
    returnHallPass(pass.id);
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
          <span>{getDestinationLabel(pass.destination)}</span>
        </div>
      </div>

      <div
        className={`text-3xl font-sans font-bold tabular-nums ${
          isOverdue ? 'text-emergency' : 'text-gray-800'
        }`}
      >
        {formatElapsed(elapsed)}
      </div>

      <button
        onClick={handleCheckIn}
        className="mt-auto flex items-center justify-center gap-1.5 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm font-medium rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-primary active:bg-gray-300"
      >
        <LogIn size={14} />
        Tap to Check-in
      </button>
    </div>
  );
}
