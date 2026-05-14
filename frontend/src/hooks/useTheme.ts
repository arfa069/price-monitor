import { useState, useEffect, useCallback } from 'react'

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'price-monitor-theme'

function getInitialTheme(): Theme {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') {
      return stored
    }
  } catch {
    // localStorage unavailable (private mode, quota full, etc.), silently fall back
  }
  if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme)

  // Set data-theme on mount (runs once)
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    document.documentElement.style.colorScheme = theme
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      'content',
      theme === 'dark' ? '#0a0a0a' : '#ffffff',
    )
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme)
    try {
      localStorage.setItem(STORAGE_KEY, newTheme)
    } catch {
      // localStorage unavailable, silently fall back
    }
    document.documentElement.setAttribute('data-theme', newTheme)
    document.documentElement.style.colorScheme = newTheme
    document.querySelector('meta[name="theme-color"]')?.setAttribute(
      'content',
      newTheme === 'dark' ? '#0a0a0a' : '#ffffff',
    )
  }, [])

  const toggleTheme = useCallback(() => {
    setTheme(theme === 'light' ? 'dark' : 'light')
  }, [theme, setTheme])

  // Listen for system preference changes
  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = (e: MediaQueryListEvent) => {
      try {
        const stored = localStorage.getItem(STORAGE_KEY)
        if (!stored) {
          const next = e.matches ? 'dark' : 'light'
          setThemeState(next)
          document.documentElement.setAttribute('data-theme', next)
          document.documentElement.style.colorScheme = next
          document.querySelector('meta[name="theme-color"]')?.setAttribute(
            'content',
            next === 'dark' ? '#0a0a0a' : '#ffffff',
          )
        }
      } catch {
        // localStorage unavailable, follow system preference directly
        setThemeState(e.matches ? 'dark' : 'light')
      }
    }
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  return { theme, setTheme, toggleTheme }
}
