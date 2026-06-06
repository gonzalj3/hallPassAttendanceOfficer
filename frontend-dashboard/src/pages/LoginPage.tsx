import { useState } from 'react';
import { signIn, type DemoRole } from '../api/auth';

const BRAND = '#00666e';

export function LoginPage({ onSignedIn }: { onSignedIn: () => void }) {
  const [busy, setBusy] = useState<DemoRole | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function pick(role: DemoRole) {
    setBusy(role);
    setError(null);
    try {
      await signIn(role);
      onSignedIn();
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-6 py-12">
      <div className="w-full max-w-lg">
        <div className="text-center mb-10">
          <div
            className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
            style={{ backgroundColor: BRAND }}
          >
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
              <rect x="9" y="3" width="6" height="4" rx="2" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Monitor Lizzie</h1>
          <p className="text-gray-500 mt-2">Operations Console</p>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <button
            type="button"
            onClick={() => pick('TEACHER')}
            disabled={busy !== null}
            className="rounded-2xl border-2 border-gray-200 hover:border-gray-300 bg-white p-6 text-left disabled:opacity-60 disabled:cursor-not-allowed transition-colors min-h-[160px] flex flex-col justify-between"
          >
            <div>
              <div className="text-3xl mb-3">🧑‍🏫</div>
              <div className="font-semibold text-lg text-gray-900">Teacher</div>
              <div className="text-sm text-gray-500 mt-1">
                Use the iPad app instead
              </div>
            </div>
            <div className="text-sm text-gray-400">
              {busy === 'TEACHER' ? 'Signing in…' : 'Wrong app for this role'}
            </div>
          </button>

          <button
            type="button"
            onClick={() => pick('ADMIN')}
            disabled={busy !== null}
            className="rounded-2xl border-2 border-gray-200 hover:border-gray-300 bg-white p-6 text-left disabled:opacity-60 disabled:cursor-not-allowed transition-colors min-h-[160px] flex flex-col justify-between"
          >
            <div>
              <div className="text-3xl mb-3">🏫</div>
              <div className="font-semibold text-lg text-gray-900">Principal</div>
              <div className="text-sm text-gray-500 mt-1">Dr. Chen · Lincoln High</div>
            </div>
            <div className="text-sm font-medium" style={{ color: BRAND }}>
              {busy === 'ADMIN' ? 'Signing in…' : 'Continue →'}
            </div>
          </button>
        </div>

        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        <p className="text-center text-xs text-gray-400 mt-10">
          Demo software · no real student data
        </p>
      </div>
    </div>
  );
}
