import { type ReactNode, useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { getMe, type CurrentUser, type DemoRole } from '../api/auth';

interface Props {
  children: ReactNode;
  role?: DemoRole;
}

export function RequireAuth({ children, role }: Props) {
  const [state, setState] = useState<'loading' | 'unauth' | 'forbidden' | 'ok'>(
    'loading',
  );
  const [_user, setUser] = useState<CurrentUser | null>(null);
  const location = useLocation();

  useEffect(() => {
    void (async () => {
      const me = await getMe();
      if (!me) {
        setState('unauth');
        return;
      }
      if (role && me.role !== role) {
        setUser(me);
        setState('forbidden');
        return;
      }
      setUser(me);
      setState('ok');
    })();
  }, [role]);

  if (state === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Loading…
      </div>
    );
  }
  if (state === 'unauth') {
    return <Navigate to="/" replace state={{ from: location }} />;
  }
  if (state === 'forbidden') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center">
        <h1 className="text-2xl font-bold mb-2">Not authorized</h1>
        <p className="text-gray-600 max-w-md">
          This view is only available to {role === 'ADMIN' ? 'principals' : 'teachers'}.
        </p>
      </div>
    );
  }
  return <>{children}</>;
}
