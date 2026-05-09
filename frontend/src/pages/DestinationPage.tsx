import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  ArrowLeft,
  HelpCircle,
  Settings,
  User,
  Bath,
  Building2,
  Stethoscope,
  Footprints,
  DoorOpen,
  Users,
} from 'lucide-react';
import { useApp } from '../context/AppContext';
import { mockStudents } from '../data/mockData';
import type { Destination } from '../types';

interface DestinationCardProps {
  destination: Destination;
  label: string;
  subtitle: string;
  icon: React.ReactNode;
  isFull?: boolean;
  isSelected: boolean;
  borderColor?: string;
  onClick: () => void;
}

function DestinationCard({
  destination: _destination,
  label,
  subtitle,
  icon,
  isFull = false,
  isSelected,
  borderColor,
  onClick,
}: DestinationCardProps) {
  const disabled = isFull;

  return (
    <button
      onClick={!disabled ? onClick : undefined}
      disabled={disabled}
      className={`relative flex flex-col items-center justify-center gap-3 p-5 rounded-lg min-h-[120px] w-full transition-all focus:outline-none focus:ring-2 focus:ring-offset-1 ${
        disabled
          ? 'bg-gray-100 border-2 border-gray-200 opacity-60 cursor-not-allowed'
          : 'bg-white border-2 hover:shadow-md active:scale-[0.98]'
      }`}
      style={
        !disabled
          ? {
              borderColor: isSelected ? '#079da8' : (borderColor ?? '#e5e7eb'),
              boxShadow: isSelected
                ? '0 0 0 3px rgba(7,157,168,0.2)'
                : undefined,
            }
          : undefined
      }
    >
      {isFull && (
        <span className="absolute top-2 right-2 flex items-center gap-1 px-2 py-0.5 bg-gray-400 text-white text-xs font-bold rounded-full">
          <Users size={10} />
          Full 2/2
        </span>
      )}

      <div
        className={`p-3 rounded-full ${
          disabled ? 'bg-gray-200 text-gray-400' : ''
        }`}
        style={
          !disabled && isSelected
            ? { backgroundColor: '#079da8', color: 'white' }
            : !disabled && borderColor
              ? { backgroundColor: `${borderColor}18`, color: borderColor }
              : !disabled
                ? { backgroundColor: '#f3f4f6', color: '#6b7280' }
                : undefined
        }
      >
        {icon}
      </div>

      <div className="text-center">
        <p
          className={`font-bold text-sm ${disabled ? 'text-gray-400' : 'text-gray-900'}`}
        >
          {label}
        </p>
        <p
          className={`text-xs mt-0.5 ${disabled ? 'text-gray-400' : 'text-gray-500'}`}
        >
          {isFull ? 'Capacity reached for this period' : subtitle}
        </p>
      </div>

      {isSelected && !disabled && (
        <div
          className="absolute top-2 right-2 w-5 h-5 rounded-full flex items-center justify-center"
          style={{ backgroundColor: '#079da8' }}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path
              d="M2 6l3 3 5-5"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      )}
    </button>
  );
}

const destinationDefs: Array<{
  destination: Destination;
  label: string;
  subtitle: string;
  icon: React.ReactNode;
  isFull?: boolean;
  borderColor?: string;
}> = [
  {
    destination: 'RESTROOM',
    label: 'Restroom',
    subtitle: 'Nearest Restroom',
    icon: <Bath size={24} />,
    borderColor: '#2563eb', // blue
  },
  {
    destination: 'HALLWAY',
    label: 'Hallway',
    subtitle: 'Water fountain or Locker access',
    icon: <Footprints size={24} />,
    borderColor: '#d97706', // amber
  },
  {
    destination: 'OFFICE',
    label: 'Office',
    subtitle: 'Main Office / Guidance',
    icon: <Building2 size={24} />,
    borderColor: '#7c3aed', // purple
  },
  {
    destination: 'NURSE',
    label: 'Nurse',
    subtitle: 'Medical Clinic Room 102',
    icon: <Stethoscope size={24} />,
    borderColor: '#dc2626', // red
  },
  {
    destination: 'CLASSROOM',
    label: 'Classroom',
    subtitle: 'Delivery or Teacher meeting',
    icon: <DoorOpen size={24} />,
    borderColor: '#059669', // green
  },
];

export function DestinationPage() {
  const navigate = useNavigate();
  const { studentId } = useParams<{ studentId: string }>();
  const {
    selectedStudent,
    setSelectedStudent,
    selectedDestination,
    setSelectedDestination,
  } = useApp();

  const student =
    selectedStudent ??
    mockStudents.find(s => s.id === studentId) ??
    mockStudents[0];

  const firstName = student.name.split(' ')[0];

  const handleSelectDestination = (destination: Destination) => {
    setSelectedDestination(destination);
    navigate('/pass-active');
  };

  const handleBack = () => {
    setSelectedStudent(null);
    setSelectedDestination(null);
    navigate(-1);
  };

  return (
    <div
      className="min-h-screen font-sans"
      style={{ backgroundColor: '#f0f0ea' }}
    >
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <button
            onClick={handleBack}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 min-h-[44px] px-1 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300 transition-colors"
          >
            <ArrowLeft size={20} />
            <div className="text-left">
              <span className="block font-bold text-base text-gray-900 leading-none">
                HallPass Pro
              </span>
              <span className="block text-xs text-gray-400 mt-0.5">
                Lincoln High &bull; Room 204
              </span>
            </div>
          </button>
          <div className="flex items-center gap-1">
            <button className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300">
              <HelpCircle size={20} />
            </button>
            <button className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300">
              <Settings size={20} />
            </button>
            <button className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300">
              <User size={20} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 pb-28">
        {/* Student Badge */}
        <div className="flex justify-center mb-6">
          <div
            className="flex items-center gap-2 px-5 py-2.5 rounded-full text-white text-sm font-semibold"
            style={{ backgroundColor: '#056778' }}
          >
            <User size={15} />
            Student Selected: {student.name}
          </div>
        </div>

        <div className="text-center mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
            Where are you going, {firstName}?
          </h1>
          <p className="text-gray-500 text-base">
            Select a destination to generate your digital hall pass.
          </p>
        </div>

        {/* Destination Grid — 3 on top, 2 on bottom centered */}
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {destinationDefs.slice(0, 3).map(d => (
              <DestinationCard
                key={d.destination}
                {...d}
                isSelected={selectedDestination === d.destination}
                onClick={() => handleSelectDestination(d.destination)}
              />
            ))}
          </div>
          <div className="grid grid-cols-3 gap-4">
            {destinationDefs.slice(3).map(d => (
              <DestinationCard
                key={d.destination}
                {...d}
                isSelected={selectedDestination === d.destination}
                onClick={() => handleSelectDestination(d.destination)}
              />
            ))}
            {/* Empty placeholder for grid alignment */}
            <div />
          </div>
        </div>
      </main>
    </div>
  );
}
