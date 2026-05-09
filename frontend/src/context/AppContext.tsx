import React, { createContext, useContext, useState, useCallback } from 'react';
import type { ClassPeriodApi, StudentApi } from '../api/types';
import type { Destination } from '../types';

// Navigation-only state. Active passes are owned by RosterPage and
// re-fetched from the API rather than mirrored here.
interface AppState {
  selectedSession: ClassPeriodApi | null;
  emergencyLock: boolean;
  selectedStudent: StudentApi | null;
  selectedDestination: Destination | null;
}

interface AppContextType extends AppState {
  setSelectedSession: (session: ClassPeriodApi | null) => void;
  setEmergencyLock: (locked: boolean) => void;
  setSelectedStudent: (student: StudentApi | null) => void;
  setSelectedDestination: (destination: Destination | null) => void;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [selectedSession, setSelectedSessionState] = useState<ClassPeriodApi | null>(null);
  const [emergencyLock, setEmergencyLockState] = useState(false);
  const [selectedStudent, setSelectedStudentState] = useState<StudentApi | null>(null);
  const [selectedDestination, setSelectedDestinationState] = useState<Destination | null>(null);

  const setSelectedSession = useCallback((session: ClassPeriodApi | null) => {
    setSelectedSessionState(session);
  }, []);

  const setEmergencyLock = useCallback((locked: boolean) => {
    setEmergencyLockState(locked);
  }, []);

  const setSelectedStudent = useCallback((student: StudentApi | null) => {
    setSelectedStudentState(student);
  }, []);

  const setSelectedDestination = useCallback((destination: Destination | null) => {
    setSelectedDestinationState(destination);
  }, []);

  const value: AppContextType = {
    selectedSession,
    emergencyLock,
    selectedStudent,
    selectedDestination,
    setSelectedSession,
    setEmergencyLock,
    setSelectedStudent,
    setSelectedDestination,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextType {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
