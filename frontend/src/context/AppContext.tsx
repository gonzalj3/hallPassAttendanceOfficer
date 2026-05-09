import React, { createContext, useContext, useState, useCallback } from 'react';
import type { AppContextType, AppState, ClassPeriod, HallPass, Student, Destination } from '../types';
import { createInitialHallPasses } from '../data/mockData';

const AppContext = createContext<AppContextType | null>(null);

const initialState: AppState = {
  selectedSession: null,
  activePasses: createInitialHallPasses(),
  emergencyLock: false,
  selectedStudent: null,
  selectedDestination: null,
};

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [selectedSession, setSelectedSessionState] = useState<ClassPeriod | null>(
    initialState.selectedSession
  );
  const [activePasses, setActivePasses] = useState<HallPass[]>(initialState.activePasses);
  const [emergencyLock, setEmergencyLockState] = useState(initialState.emergencyLock);
  const [selectedStudent, setSelectedStudentState] = useState<Student | null>(
    initialState.selectedStudent
  );
  const [selectedDestination, setSelectedDestinationState] = useState<Destination | null>(
    initialState.selectedDestination
  );

  const setSelectedSession = useCallback((session: ClassPeriod | null) => {
    setSelectedSessionState(session);
  }, []);

  const addHallPass = useCallback((pass: HallPass) => {
    setActivePasses((prev) => [...prev, pass]);
  }, []);

  const returnHallPass = useCallback((passId: string) => {
    setActivePasses((prev) =>
      prev.map((p) => (p.id === passId ? { ...p, status: 'RETURNED' as const } : p))
    );
  }, []);

  const setEmergencyLock = useCallback((locked: boolean) => {
    setEmergencyLockState(locked);
  }, []);

  const setSelectedStudent = useCallback((student: Student | null) => {
    setSelectedStudentState(student);
  }, []);

  const setSelectedDestination = useCallback((destination: Destination | null) => {
    setSelectedDestinationState(destination);
  }, []);

  const value: AppContextType = {
    selectedSession,
    activePasses,
    emergencyLock,
    selectedStudent,
    selectedDestination,
    setSelectedSession,
    addHallPass,
    returnHallPass,
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
