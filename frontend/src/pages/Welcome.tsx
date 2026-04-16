import React from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowRight,
  Moon,
  Sun,
  Zap,
  Users,
  Sparkles,
  GitBranch,
  Layers,
} from 'lucide-react'

import { useI18n } from '../i18n'
import { cn } from '../lib/utils'
import { useThemeStore } from '../stores/useThemeStore'

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 },
}

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1,
    },
  },
}

const floatAnimation = {
  animate: {
    y: [0, -10, 0],
    transition: {
      duration: 3,
      repeat: Infinity,
      ease: 'easeInOut' as const,
    },
  },
}

export const Welcome: React.FC = () => {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useThemeStore()

  const handleGetStarted = () => {
    const token = localStorage.getItem('token')
    const isGuest = localStorage.getItem('isGuest')
    if (token || isGuest) {
      navigate('/rooms')
    } else {
      navigate('/login')
    }
  }

  const handleQuickStart = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.setItem('isGuest', 'true')
    navigate('/rooms')
  }

  const isDark = theme === 'dark'

  const features = [
    {
      icon: Users,
      title: t('welcome.feature.multiplayer.title'),
      desc: t('welcome.feature.multiplayer.description'),
      gradient: 'from-blue-500 to-cyan-500',
    },
    {
      icon: Sparkles,
      title: t('welcome.feature.ai.title'),
      desc: t('welcome.feature.ai.description'),
      gradient: 'from-violet-500 to-purple-500',
    },
    {
      icon: GitBranch,
      title: t('welcome.feature.versioning.title'),
      desc: t('welcome.feature.versioning.description'),
      gradient: 'from-orange-500 to-rose-500',
    },
  ]

  return (
    <div
      className={cn(
        'relative flex min-h-screen flex-col overflow-hidden',
        isDark
          ? 'bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950'
          : 'bg-gradient-to-br from-slate-50 via-white to-blue-50',
      )}
    >
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div
          className={cn(
            'absolute -right-40 -top-40 h-96 w-96 rounded-full opacity-30 blur-3xl',
            isDark ? 'bg-blue-600' : 'bg-blue-400',
          )}
        />
        <div
          className={cn(
            'absolute -bottom-40 -left-40 h-96 w-96 rounded-full opacity-30 blur-3xl',
            isDark ? 'bg-violet-600' : 'bg-violet-400',
          )}
        />
        <div
          className={cn('absolute inset-0 opacity-[0.02]', isDark && 'opacity-[0.05]')}
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23${isDark ? 'fff' : '000'}' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
          }}
        />
      </div>

      <motion.header
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn(
          'relative z-10 flex items-center justify-between px-6 py-4 md:px-12',
          isDark ? 'border-slate-800' : 'border-slate-200',
        )}
      >
        <div className="flex items-center gap-3">
          <motion.div
            whileHover={{ scale: 1.05, rotate: 5 }}
            className={cn(
              'flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-blue-500 via-indigo-500 to-violet-600 font-bold text-white shadow-lg',
            )}
          >
            <Layers size={20} />
          </motion.div>
          <span className={cn('text-xl font-bold tracking-tight', isDark ? 'text-white' : 'text-slate-900')}>
            SyncCanvas
          </span>
        </div>

        <motion.button
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={toggleTheme}
          className={cn(
            'rounded-xl p-2.5 transition-all duration-300',
            isDark
              ? 'border border-slate-700 bg-slate-800/50 text-yellow-400 hover:bg-slate-700/50'
              : 'border border-slate-200 bg-white/50 text-slate-600 shadow-sm hover:bg-white',
          )}
        >
          {isDark ? <Sun size={18} /> : <Moon size={18} />}
        </motion.button>
      </motion.header>

      <main className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 pb-20">
        <motion.div
          className="w-full max-w-2xl text-center"
          variants={staggerContainer}
          initial="initial"
          animate="animate"
        >
          <motion.div variants={fadeInUp} className="mb-6">
            <span
              className={cn(
                'inline-flex items-center gap-2 rounded-full px-4 py-1.5 text-sm font-medium',
                isDark
                  ? 'border border-blue-500/20 bg-blue-500/10 text-blue-400'
                  : 'border border-blue-100 bg-blue-50 text-blue-600',
              )}
            >
              <Sparkles size={14} />
              {t('welcome.badge')}
            </span>
          </motion.div>

          <motion.h1
            variants={fadeInUp}
            className={cn(
              'mb-6 text-4xl font-extrabold leading-tight sm:text-5xl md:text-6xl',
              isDark ? 'text-white' : 'text-slate-900',
            )}
          >
            <span className="bg-gradient-to-r from-blue-500 via-violet-500 to-purple-500 bg-clip-text text-transparent">
              {t('welcome.headingHighlight')}
            </span>
            <br />
            {t('welcome.headingSuffix')}
          </motion.h1>

          <motion.p
            variants={fadeInUp}
            className={cn(
              'mx-auto mb-10 max-w-lg text-lg leading-relaxed md:text-xl',
              isDark ? 'text-slate-400' : 'text-slate-600',
            )}
          >
            {t('welcome.descriptionPrefix')}
            <span className={cn('font-medium', isDark ? 'text-violet-400' : 'text-violet-600')}>
              {t('welcome.descriptionHighlight')}
            </span>
            {t('welcome.descriptionSuffix')}
          </motion.p>

          <motion.div
            variants={fadeInUp}
            className="mb-16 flex flex-col justify-center gap-4 sm:flex-row"
          >
            <motion.button
              whileHover={{ scale: 1.02, boxShadow: '0 20px 40px -15px rgba(59, 130, 246, 0.5)' }}
              whileTap={{ scale: 0.98 }}
              onClick={handleGetStarted}
              className={cn(
                'flex items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600 px-8 py-4 text-lg font-semibold text-white shadow-xl shadow-blue-500/25 transition-all duration-300',
              )}
            >
              {t('welcome.getStarted')}
              <ArrowRight size={20} />
            </motion.button>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleQuickStart}
              className={cn(
                'flex items-center justify-center gap-2 rounded-2xl border-2 px-8 py-4 text-lg font-semibold transition-all duration-300',
                isDark
                  ? 'border-slate-700 text-slate-300 hover:border-slate-600 hover:bg-slate-800/50'
                  : 'border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-white hover:shadow-lg',
              )}
            >
              <Zap size={20} className="text-yellow-500" />
              {t('welcome.guestExperience')}
            </motion.button>
          </motion.div>

          <motion.div variants={fadeInUp} className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                variants={floatAnimation}
                animate="animate"
                style={{ animationDelay: `${index * 0.5}s` }}
                whileHover={{ scale: 1.05, y: -5 }}
                className={cn(
                  'rounded-2xl p-6 backdrop-blur-sm transition-all duration-300',
                  isDark
                    ? 'border border-slate-700/50 bg-slate-800/30 hover:border-slate-600'
                    : 'border border-slate-200/50 bg-white/60 hover:border-slate-300 hover:shadow-xl',
                )}
              >
                <div
                  className={cn(
                    'mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl text-white shadow-lg',
                    `bg-gradient-to-br ${feature.gradient}`,
                  )}
                >
                  <feature.icon size={24} />
                </div>
                <h3 className={cn('mb-2 text-lg font-bold', isDark ? 'text-white' : 'text-slate-900')}>
                  {feature.title}
                </h3>
                <p className={cn('text-sm', isDark ? 'text-slate-400' : 'text-slate-500')}>
                  {feature.desc}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </motion.div>
      </main>

      <motion.footer
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.5 }}
        className={cn(
          'relative z-10 py-6 text-center text-sm',
          isDark ? 'text-slate-600' : 'text-slate-400',
        )}
      >
        <span className="inline-flex items-center gap-2">
          {t('welcome.footer')}
          <span className="text-red-400">♥</span>
        </span>
      </motion.footer>
    </div>
  )
}
