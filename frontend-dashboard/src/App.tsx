import { useEffect, useState } from 'react';
import AdminDashboard from './pages/AdminDashboard';
import { LoginPage } from './pages/LoginPage';
import { getMe, signOut, type CurrentUser } from './api/auth';

type AuthState =
  | { status: 'loading' }
  | { status: 'unauth' }
  | { status: 'forbidden'; user: CurrentUser }
  | { status: 'ok'; user: CurrentUser };

export default function App() {
  const [auth, setAuth] = useState<AuthState>({ status: 'loading' });

  async function refresh() {
    const me = await getMe();
    if (!me) {
      setAuth({ status: 'unauth' });
    } else if (me.role !== 'ADMIN') {
      setAuth({ status: 'forbidden', user: me });
    } else {
      setAuth({ status: 'ok', user: me });
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  if (auth.status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Loading…
      </div>
    );
  }
  if (auth.status === 'unauth') {
    return <LoginPage onSignedIn={() => void refresh()} />;
  }
  if (auth.status === 'forbidden') {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center">
        <h1 className="text-2xl font-bold mb-2">Wrong app</h1>
        <p className="text-gray-600 max-w-md mb-6">
          The Operations Console is for principals. Teachers should use the
          iPad app instead.
        </p>
        <button
          type="button"
          className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
          onClick={async () => {
            await signOut();
            void refresh();
          }}
        >
          Sign out
        </button>
      </div>
    );
  }
  return <AdminDashboard />;
}
