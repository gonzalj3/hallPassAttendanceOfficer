import { useNavigate } from 'react-router-dom';
import { Settings, HelpCircle, User, Sparkles, Calendar } from 'lucide-react';
import { mockClasses } from '../data/mockData';
import { useApp } from '../context/AppContext';
import { EmergencyLockButton } from '../components/EmergencyLockButton';
import type { ClassPeriod } from '../types';

function ClassCard({ period, onClick }: { period: ClassPeriod; onClick: () => void }) {
  const isSuggested = period.type === 'suggested';
  const isAdvisory = period.type === 'advisory';
  const isLunch = period.type === 'lunch';

  let bgColor = 'bg-white';
  let borderClass = 'border border-gray-100';

  if (isSuggested) {
    bgColor = '';
    borderClass = 'border-2';
  } else if (isAdvisory) {
    bgColor = '';
    borderClass = 'border border-orange-200';
  } else if (isLunch) {
    bgColor = 'bg-gray-50';
    borderClass = 'border border-gray-200';
  }

  return (
    <button
      onClick={onClick}
      className={`${bgColor} ${borderClass} rounded-lg p-5 text-left w-full transition-all hover:shadow-md active:scale-[0.98] focus:outline-none focus:ring-2 focus:ring-offset-1 min-h-[100px] flex flex-col justify-between`}
      style={
        isSuggested
          ? { backgroundColor: '#e8f5f6', borderColor: '#079da8' }
          : isAdvisory
          ? { backgroundColor: '#fef3e2' }
          : undefined
      }
    >
      {isSuggested && (
        <div className="flex items-center justify-between mb-3">
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wide"
            style={{ backgroundColor: '#079da8', color: 'white' }}
          >
            <Sparkles size={11} />
            SUGGESTED
          </div>
          <span className="text-xs text-gray-500">Current Period based on Schedule</span>
        </div>
      )}

      <div>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p
              className={`font-bold text-gray-900 ${isSuggested ? 'text-lg' : 'text-base'}`}
            >
              {period.period}
            </p>
            <p
              className={`font-semibold ${isSuggested ? 'text-base' : 'text-sm'} text-gray-700 mt-0.5`}
            >
              {period.name}
            </p>
          </div>
          {period.studentCount > 0 && (
            <span className="text-xs font-medium text-gray-400 mt-0.5 whitespace-nowrap">
              {period.studentCount} students
            </span>
          )}
        </div>

        <p className="text-sm text-gray-500 mt-2">
          {period.startTime} — {period.endTime}
        </p>
        {period.room && (
          <p className="text-xs text-gray-400 mt-1">Room {period.room}</p>
        )}
      </div>
    </button>
  );
}

export function ClassSelectPage() {
  const navigate = useNavigate();
  const { setSelectedSession } = useApp();

  const suggestedClass = mockClasses.find((c) => c.type === 'suggested');
  const otherClasses = mockClasses.filter((c) => c.type !== 'suggested');

  const handleSelectClass = (period: ClassPeriod) => {
    setSelectedSession(period);
    navigate(`/roster/${period.id}`);
  };

  return (
    <div className="min-h-screen font-sans" style={{ backgroundColor: '#f0f0ea' }}>
      {/* Header */}
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: '#079da8' }}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
                <rect x="9" y="3" width="6" height="4" rx="2" />
                <path d="M9 12h6" />
                <path d="M9 16h4" />
              </svg>
            </div>
            <span className="font-bold text-lg text-gray-900">HallPass Pro</span>
          </div>
          <div className="flex items-center gap-1">
            <button className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300">
              <Settings size={20} />
            </button>
            <button className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300">
              <HelpCircle size={20} />
            </button>
            <button className="p-2 rounded-lg text-gray-500 hover:bg-gray-100 min-h-[44px] min-w-[44px] flex items-center justify-center transition-colors focus:outline-none focus:ring-2 focus:ring-gray-300">
              <User size={20} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 pb-28">
        <div className="text-center mb-8">
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
            Select Your Current Class
          </h1>
          <p className="text-gray-500 text-base max-w-xl mx-auto">
            Tap the period you are currently teaching to view the roster and active passes.
          </p>
        </div>

        {/* Suggested Card */}
        {suggestedClass && (
          <div className="mb-4">
            <ClassCard period={suggestedClass} onClick={() => handleSelectClass(suggestedClass)} />
          </div>
        )}

        {/* Other Classes Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {otherClasses.map((period) => (
            <ClassCard key={period.id} period={period} onClick={() => handleSelectClass(period)} />
          ))}
        </div>

        {/* Schedule Info */}
        <div className="mt-6 flex items-center gap-2 text-sm text-gray-400">
          <Calendar size={15} />
          <span>Schedule for Monday, Oct 23rd</span>
        </div>
      </main>

      {/* Emergency Lock - fixed bottom right */}
      <div className="fixed bottom-6 right-6 z-20">
        <EmergencyLockButton variant="default" />
      </div>
    </div>
  );
}
