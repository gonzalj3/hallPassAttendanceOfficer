import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function GoogleIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="#34A853"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="#FBBC05"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="#EA4335"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

function MicrosoftIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <rect x="1" y="1" width="10" height="10" fill="#F25022" />
      <rect x="13" y="1" width="10" height="10" fill="#7FBA00" />
      <rect x="1" y="13" width="10" height="10" fill="#00A4EF" />
      <rect x="13" y="13" width="10" height="10" fill="#FFB900" />
    </svg>
  );
}

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');

  const handleContinue = (e: React.FormEvent) => {
    e.preventDefault();
    navigate('/classes');
  };

  const handleSSOLogin = () => {
    navigate('/classes');
  };

  return (
    <div className="min-h-screen flex font-sans">
      {/* Left Panel */}
      <div
        className="hidden md:flex flex-col justify-between p-10 lg:p-14"
        style={{ backgroundColor: '#079da8', width: '40%' }}
      >
        <div>
          <div className="flex items-center gap-2 mb-12">
            <div className="w-9 h-9 bg-white bg-opacity-20 rounded-lg flex items-center justify-center">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
                <rect x="9" y="3" width="6" height="4" rx="2" />
                <path d="M9 12h6" />
                <path d="M9 16h4" />
              </svg>
            </div>
            <span className="text-white font-bold text-xl tracking-tight">HallPass Pro</span>
          </div>

          <div className="mt-16">
            <h1 className="text-4xl lg:text-5xl font-black text-white leading-tight mb-6">
              Streamlining Student Success.
            </h1>
            <p className="text-white text-opacity-90 text-lg leading-relaxed" style={{ color: 'rgba(255,255,255,0.88)' }}>
              Manage classroom movement with high-contrast clarity and professional safety standards.
            </p>
          </div>
        </div>

        <div className="mt-auto">
          <div className="border-t border-white border-opacity-20 pt-6">
            <p className="text-sm" style={{ color: 'rgba(255,255,255,0.75)' }}>
              Trusted by over 500 school districts nationwide.
            </p>
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="flex-1 flex items-center justify-center bg-white px-6 py-12 sm:px-10 lg:px-16">
        <div className="w-full max-w-md">
          {/* Mobile logo */}
          <div className="flex items-center gap-2 mb-8 md:hidden">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: '#079da8' }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
                <rect x="9" y="3" width="6" height="4" rx="2" />
              </svg>
            </div>
            <span className="font-bold text-lg" style={{ color: '#079da8' }}>HallPass Pro</span>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome Back</h2>
          <p className="text-gray-500 mb-8 text-base">
            Access your classroom dashboard to manage student passes.
          </p>

          {/* SSO Buttons */}
          <div className="space-y-3 mb-6">
            <button
              onClick={handleSSOLogin}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400 active:bg-gray-300"
            >
              <GoogleIcon />
              <span>Sign in with Google</span>
            </button>
            <button
              onClick={handleSSOLogin}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-800 font-medium rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400 active:bg-gray-300"
            >
              <MicrosoftIcon />
              <span>Sign in with Microsoft</span>
            </button>
          </div>

          {/* Divider */}
          <div className="relative flex items-center gap-3 mb-6">
            <div className="flex-1 h-px bg-gray-200" />
            <span className="text-sm text-gray-400 whitespace-nowrap">or use school email</span>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          {/* Email Form */}
          <form onSubmit={handleContinue} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                Email Address
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="teacher@school.edu"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:border-transparent min-h-[44px] text-base"
                style={{ '--tw-ring-color': '#079da8' } as React.CSSProperties}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = '#079da8';
                  e.currentTarget.style.boxShadow = '0 0 0 2px rgba(7,157,168,0.2)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = '';
                  e.currentTarget.style.boxShadow = '';
                }}
              />
            </div>
            <button
              type="submit"
              className="w-full py-3 text-white font-semibold rounded-lg min-h-[44px] transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 active:opacity-90"
              style={{ backgroundColor: '#079da8' }}
              onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#068090')}
              onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#079da8')}
            >
              Continue
            </button>
          </form>

          <p className="text-center text-sm text-gray-400 mt-8">
            Need help accessing your account?{' '}
            <a
              href="#"
              className="font-medium underline hover:opacity-80"
              style={{ color: '#079da8' }}
            >
              Contact Support
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
