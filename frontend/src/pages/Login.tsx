import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Moon, Sun, User, Users } from 'lucide-react';

import { config } from '../config/env';
import { useI18n } from '../i18n';
import { cn } from '../lib/utils';
import { getRequestErrorMessage } from '../services/api/axios';
import { useThemeStore } from '../stores/useThemeStore';

export const Login: React.FC = () => {
  const { t } = useI18n();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { theme, toggleTheme } = useThemeStore();

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError('');

    const endpoint = '/auth/token';
    const body = new URLSearchParams({ username, password });

    try {
      const response = await fetch(`${config.apiBaseUrl}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || t('login.authFailed'));
      }

      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      localStorage.setItem('username', username);
      localStorage.removeItem('isGuest');
      navigate('/rooms');
    } catch (err) {
      setError(getRequestErrorMessage(err, t('login.authFailed')));
    }
  };

  const handleGuestLogin = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.setItem('isGuest', 'true');
    navigate('/rooms');
  };

  return (
    <div
      className={cn(
        'relative flex min-h-screen items-center justify-center overflow-hidden transition-all duration-500',
        theme === 'dark' ? 'bg-slate-900' : 'bg-gray-50',
      )}
    >
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            x: [0, 50, 0],
            y: [0, 30, 0],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className={cn(
            'absolute -left-[10%] -top-[20%] h-[70%] w-[70%] rounded-full opacity-20 mix-blend-multiply blur-[100px]',
            theme === 'dark' ? 'bg-purple-900' : 'bg-purple-300',
          )}
        />
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            x: [0, -30, 0],
            y: [0, 50, 0],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 2,
          }}
          className={cn(
            'absolute -right-[10%] top-[20%] h-[70%] w-[70%] rounded-full opacity-20 mix-blend-multiply blur-[100px]',
            theme === 'dark' ? 'bg-indigo-900' : 'bg-indigo-300',
          )}
        />
        <motion.div
          animate={{
            scale: [1, 1.3, 1],
            x: [0, 40, 0],
            y: [0, -40, 0],
          }}
          transition={{
            duration: 18,
            repeat: Infinity,
            ease: 'easeInOut',
            delay: 4,
          }}
          className={cn(
            'absolute -bottom-[20%] left-[20%] h-[70%] w-[70%] rounded-full opacity-20 mix-blend-multiply blur-[100px]',
            theme === 'dark' ? 'bg-blue-900' : 'bg-blue-300',
          )}
        />
      </div>

      <button
        onClick={toggleTheme}
        className={cn(
          'absolute right-6 top-6 z-10 rounded-full border p-3 backdrop-blur-md transition-all duration-300',
          theme === 'dark'
            ? 'border-slate-700 bg-slate-800/50 text-slate-300 hover:bg-slate-700/50'
            : 'border-white/50 bg-white/50 text-slate-600 shadow-sm hover:bg-white/80',
        )}
      >
        {theme === 'dark' ? <Moon size={20} /> : <Sun size={20} />}
      </button>

      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className={cn(
          'relative mx-4 w-full max-w-md rounded-3xl border p-8 shadow-2xl backdrop-blur-xl transition-all duration-300 md:p-10',
          theme === 'dark'
            ? 'border-slate-700/50 bg-slate-800/40 text-slate-100 shadow-black/20'
            : 'border-white/50 bg-white/70 text-slate-800 shadow-xl',
        )}
      >
        <div className="mb-8 text-center">
          <div
            className={cn(
              'mx-auto mb-4 flex h-16 w-16 rotate-3 transform items-center justify-center rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 text-3xl font-bold text-white shadow-lg',
            )}
          >
            S
          </div>
          <h2 className={cn('mb-2 text-3xl font-bold tracking-tight', theme === 'dark' ? 'text-white' : 'text-slate-900')}>
            SyncCanvas
          </h2>
          <p className={cn('text-sm', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
            {t('login.subtitle')}
          </p>
        </div>

        {error && (
          <div className="mb-6 flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-500 animate-in slide-in-from-top-2 fade-in">
            <div className="h-1.5 w-1.5 rounded-full bg-red-500" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label className={cn('ml-1 block text-xs font-semibold uppercase tracking-wider', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
              {t('login.usernameLabel')}
            </label>
            <div className="relative">
              <User className={cn('absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 transition-colors', theme === 'dark' ? 'text-slate-500' : 'text-slate-400')} />
              <input
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className={cn(
                  'w-full rounded-xl border py-3 pl-10 pr-4 outline-none transition-all duration-200',
                  theme === 'dark'
                    ? 'border-slate-700 bg-slate-900/50 text-slate-100 placeholder:text-slate-600 focus:border-blue-500 focus:bg-slate-900/80'
                    : 'border-slate-200 bg-white/50 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white',
                )}
                placeholder={t('login.usernamePlaceholder')}
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className={cn('ml-1 block text-xs font-semibold uppercase tracking-wider', theme === 'dark' ? 'text-slate-400' : 'text-slate-500')}>
              {t('login.passwordLabel')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className={cn(
                'w-full rounded-xl border px-4 py-3 outline-none transition-all duration-200',
                theme === 'dark'
                  ? 'border-slate-700 bg-slate-900/50 text-slate-100 placeholder:text-slate-600 focus:border-blue-500 focus:bg-slate-900/80 focus:ring-2 focus:ring-blue-500/20'
                  : 'border-slate-200 bg-white/50 text-slate-900 placeholder:text-slate-400 focus:border-blue-500 focus:bg-white focus:ring-2 focus:ring-blue-500/20',
              )}
              placeholder={t('login.passwordPlaceholder')}
              required
            />
          </div>

          <motion.button
            whileHover={{ scale: 1.02, boxShadow: '0 10px 20px -10px rgba(59, 130, 246, 0.5)' }}
            whileTap={{ scale: 0.98 }}
            type="submit"
            className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-3.5 font-semibold text-white shadow-lg shadow-blue-500/25 transition-all duration-200 hover:from-blue-700 hover:to-indigo-700"
          >
            {t('login.submit')}
          </motion.button>
        </form>

        <div className="relative my-8">
          <div className="absolute inset-0 flex items-center">
            <div className={cn('w-full border-t', theme === 'dark' ? 'border-slate-700' : 'border-slate-200')} />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className={cn('px-4 text-xs font-medium uppercase tracking-wider', theme === 'dark' ? 'bg-slate-800 text-slate-500' : 'bg-white text-slate-400')}>
              {t('login.or')}
            </span>
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleGuestLogin}
          className={cn(
            'flex w-full items-center justify-center gap-2 rounded-xl border py-3.5 font-medium transition-all duration-200',
            theme === 'dark'
              ? 'border-slate-700 text-slate-300 hover:bg-slate-700/50'
              : 'border-slate-200 text-slate-600 hover:bg-slate-50',
          )}
        >
          <Users size={18} />
          {t('login.guestAccess')}
        </motion.button>
      </motion.div>
    </div>
  );
};
