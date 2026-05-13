/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import { useTheme, type Theme } from '@/hooks/useTheme'
import type { MotionSpeed } from '@/types/motion'

const MOTION_SPEED_STORAGE_KEY = 'price-monitor-motion-speed'

function getInitialMotionSpeed(): MotionSpeed {
  try {
    const stored = localStorage.getItem(MOTION_SPEED_STORAGE_KEY)
    if (stored === 'fast' || stored === 'normal' || stored === 'slow') {
      return stored
    }
  } catch {
    // localStorage unavailable; fall back to the default speed.
  }
  return 'normal'
}

interface ThemeContextValue {
  theme: Theme
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  motionSpeed: MotionSpeed
  setMotionSpeed: (speed: MotionSpeed) => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function useThemeContext() {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useThemeContext must be used within ThemeProvider')
  }
  return context
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { theme, setTheme, toggleTheme } = useTheme()
  const [motionSpeed, setMotionSpeedState] = useState<MotionSpeed>(getInitialMotionSpeed)

  const setMotionSpeed = useCallback((speed: MotionSpeed) => {
    setMotionSpeedState(speed)
    try {
      localStorage.setItem(MOTION_SPEED_STORAGE_KEY, speed)
    } catch {
      // localStorage unavailable; keep the in-memory preference.
    }
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, motionSpeed, setMotionSpeed }}>
      {children}
    </ThemeContext.Provider>
  )
}
