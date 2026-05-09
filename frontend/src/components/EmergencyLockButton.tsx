import { AlertTriangle, X } from 'lucide-react';
import { useApp } from '../context/AppContext';

interface EmergencyLockButtonProps {
  className?: string;
  variant?: 'default' | 'pill' | 'full-width';
}

export function EmergencyLockButton({
  className = '',
  variant = 'default',
}: EmergencyLockButtonProps) {
  const { emergencyLock, setEmergencyLock } = useApp();

  const handleToggle = () => {
    setEmergencyLock(!emergencyLock);
  };

  const baseClasses =
    'flex items-center justify-center gap-2 font-semibold min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500';

  const variantClasses = {
    default:
      'px-4 py-2 rounded-lg bg-emergency text-white hover:bg-red-700 active:bg-red-800 shadow-md',
    pill: 'px-6 py-3 rounded-full bg-emergency text-white hover:bg-red-700 active:bg-red-800 shadow-md w-full max-w-xs',
    'full-width':
      'px-4 py-3 rounded-lg bg-emergency text-white hover:bg-red-700 active:bg-red-800 w-full',
  };

  return (
    <>
      <button
        onClick={handleToggle}
        className={`${baseClasses} ${variantClasses[variant]} ${className}`}
        aria-label="Emergency Lockdown"
      >
        <AlertTriangle size={18} />
        <span>* Emergency Lock</span>
      </button>

      {emergencyLock && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-emergency">
          <div className="text-center text-white px-8 max-w-2xl">
            <AlertTriangle size={80} className="mx-auto mb-6 animate-pulse" />
            <h1 className="text-4xl font-black uppercase tracking-widest mb-4 leading-tight">
              LOCKDOWN
            </h1>
            <p className="text-2xl font-bold uppercase tracking-wide mb-8">
              ALL STUDENTS RETURN TO CLASS IMMEDIATELY
            </p>
            <p className="text-lg mb-8 opacity-90">
              Emergency lockdown is active. All hall passes are suspended.
              Students must return to their assigned classrooms.
            </p>
            <button
              onClick={handleToggle}
              className="inline-flex items-center gap-2 px-8 py-4 bg-white text-emergency font-bold rounded-lg text-lg hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-white min-h-[44px]"
            >
              <X size={20} />
              Cancel Lockdown
            </button>
          </div>
        </div>
      )}
    </>
  );
}
