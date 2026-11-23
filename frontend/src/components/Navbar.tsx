import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Sparkles,
  MessageSquare,
  Compass,
  GitCompare,
  BarChart3,
  ShieldAlert,
  Settings,
  LogIn,
  LogOut,
  User as UserIcon,
  X,
  Lock,
} from 'lucide-react';
import { authService } from '../services/api';
import { User } from '../types';

interface NavbarProps {
  user: User | null;
  setUser: (u: User | null) => void;
  compareList: string[];
}

export const Navbar: React.FC<NavbarProps> = ({ user, setUser, compareList }) => {
  const location = useLocation();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('admin@shopmind.ai');
  const [password, setPassword] = useState('Admin@ShopMind2026!');
  const [fullName, setFullName] = useState('');
  const [authError, setAuthError] = useState('');
  const [loading, setLoading] = useState(false);

  const navItems = [
    { path: '/', label: 'Overview', icon: Sparkles },
    { path: '/assistant', label: 'AI Assistant', icon: MessageSquare },
    { path: '/explorer', label: 'Product Explorer', icon: Compass },
    {
      path: '/compare',
      label: 'Comparison',
      icon: GitCompare,
      badge: compareList.length > 0 ? compareList.length : undefined,
    },
    { path: '/evaluation', label: 'RAG Evaluation', icon: BarChart3 },
    { path: '/security', label: 'AI Security', icon: ShieldAlert },
    { path: '/admin', label: 'Admin Ops', icon: Settings },
  ];

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setLoading(true);
    try {
      const data = isLogin
        ? await authService.login(email, password)
        : await authService.register(email, fullName, password);
      setUser(data.user);
      setShowAuthModal(false);
    } catch (err: any) {
      setAuthError(err?.response?.data?.detail || 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  const quickFillRole = (role: 'admin' | 'shopper') => {
    setIsLogin(true);
    if (role === 'admin') {
      setEmail('admin@shopmind.ai');
      setPassword('Admin@ShopMind2026!');
    } else {
      setEmail('demo@shopmind.ai');
      setPassword('Shopper@2026!');
    }
  };

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-800/80 bg-[#070B14]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
          {/* Brand Logo */}
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-blue-600 shadow-lg shadow-violet-600/30">
              <Sparkles className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="bg-gradient-to-r from-white via-violet-200 to-blue-300 bg-clip-text text-lg font-extrabold tracking-tight text-transparent">
                  ShopMind AI
                </span>
                <span className="rounded-md border border-violet-500/40 bg-violet-500/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-violet-300">
                  RAG + Security
                </span>
              </div>
              <p className="text-[11px] text-slate-400">Grounded Shopping Intelligence</p>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`relative flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold transition-all ${
                    active
                      ? 'bg-gradient-to-r from-violet-600/25 to-blue-600/25 text-white border border-violet-500/40 shadow-sm'
                      : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                  }`}
                >
                  <Icon className={`h-3.5 w-3.5 ${active ? 'text-violet-400' : ''}`} />
                  {item.label}
                  {item.badge !== undefined && (
                    <span className="ml-1 rounded-full bg-violet-600 px-1.5 py-0.2 text-[10px] font-bold text-white">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          {/* Auth Status */}
          <div className="flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-2.5">
                <div className="hidden sm:flex flex-col items-end">
                  <span className="text-xs font-bold text-slate-200">{user.full_name}</span>
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-violet-400">
                    {user.role} Account
                  </span>
                </div>
                <button
                  onClick={() => {
                    authService.logout();
                    setUser(null);
                  }}
                  className="flex items-center gap-1.5 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-rose-500/50 hover:text-rose-300"
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Sign Out
                </button>
              </div>
            ) : (
              <button
                onClick={() => setShowAuthModal(true)}
                className="flex items-center gap-1.5 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-violet-600/25 transition hover:brightness-110"
              >
                <LogIn className="h-3.5 w-3.5" />
                Sign In / RBAC
              </button>
            )}
          </div>
        </div>

        {/* Mobile sub-navbar */}
        <div className="flex lg:hidden overflow-x-auto border-t border-slate-800/70 px-3 py-2 gap-1.5">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex shrink-0 items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs font-semibold ${
                  active
                    ? 'bg-violet-600/25 text-white border border-violet-500/40'
                    : 'text-slate-400 hover:bg-slate-800/60'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </Link>
            );
          })}
        </div>
      </header>

      {/* Authentication Modal */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="relative w-full max-w-md rounded-2xl border border-slate-800 bg-[#0B1120] p-6 shadow-2xl">
            <button
              onClick={() => setShowAuthModal(false)}
              className="absolute right-4 top-4 rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>

            <div className="mb-4 flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-violet-600/20 text-violet-400 border border-violet-500/30">
                <Lock className="h-4 w-4" />
              </div>
              <div>
                <h2 className="text-lg font-bold text-white">
                  {isLogin ? 'Sign In to ShopMind AI' : 'Create ShopMind Account'}
                </h2>
                <p className="text-xs text-slate-400">
                  JWT Authentication & Role-Based Access Control
                </p>
              </div>
            </div>

            {/* One-Click Demo Credentials */}
            <div className="mb-4 rounded-xl border border-slate-800 bg-slate-900/70 p-3">
              <div className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                One-Click Pre-Seeded Test Credentials
              </div>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => quickFillRole('admin')}
                  className="rounded-lg border border-violet-500/40 bg-violet-600/15 px-2.5 py-1.5 text-xs font-semibold text-violet-300 hover:bg-violet-600/25"
                >
                  Admin Architect Role
                </button>
                <button
                  type="button"
                  onClick={() => quickFillRole('shopper')}
                  className="rounded-lg border border-blue-500/40 bg-blue-600/15 px-2.5 py-1.5 text-xs font-semibold text-blue-300 hover:bg-blue-600/25"
                >
                  Demo Shopper Role
                </button>
              </div>
            </div>

            {authError && (
              <div className="mb-4 rounded-xl border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300">
                {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className="space-y-3.5">
              {!isLogin && (
                <div>
                  <label className="mb-1 block text-xs font-semibold text-slate-300">Full Name</label>
                  <input
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Aarav Sharma"
                    className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-violet-500 focus:outline-none"
                  />
                </div>
              )}
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-300">Email Address</label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-violet-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-300">Password</label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3.5 py-2.5 text-sm text-white focus:border-violet-500 focus:outline-none"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 py-2.5 text-sm font-bold text-white shadow-lg shadow-violet-600/25 transition hover:brightness-110 disabled:opacity-50"
              >
                {loading ? 'Authenticating...' : isLogin ? 'Sign In with JWT' : 'Register Account'}
              </button>
            </form>

            <div className="mt-4 text-center text-xs text-slate-400">
              {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
              <button
                type="button"
                onClick={() => setIsLogin(!isLogin)}
                className="font-bold text-violet-400 hover:underline"
              >
                {isLogin ? 'Create one' : 'Sign In'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
