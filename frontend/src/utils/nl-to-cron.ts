/**
 * Natural language → cron expression parser.
 *
 * Supports ~20 common scheduling patterns. Returns null for unparseable input.
 * Pure function — no side effects, no dependencies.
 */

export interface NlToCronResult {
  cron: string
  description: string
}

const DAY_MAP: Record<string, number> = {
  sunday: 0, sun: 0,
  monday: 1, mon: 1,
  tuesday: 2, tue: 2, tues: 2,
  wednesday: 3, wed: 3,
  thursday: 4, thu: 4, thur: 4, thurs: 4,
  friday: 5, fri: 5,
  saturday: 6, sat: 6,
}

function parseTime(
  hourStr: string,
  minuteStr?: string,
  ampm?: string,
): { hour: number; minute: number } | null {
  let hour = parseInt(hourStr, 10)
  let minute = minuteStr ? parseInt(minuteStr, 10) : 0

  if (isNaN(hour) || hour < 0 || hour > 23) return null
  if (isNaN(minute) || minute < 0 || minute > 59) return null

  if (ampm) {
    const isPm = ampm === 'pm'
    if (hour < 1 || hour > 12) return null
    if (isPm && hour !== 12) hour += 12
    if (!isPm && hour === 12) hour = 0
  }

  return { hour, minute }
}

function formatTime(hour: number, minute: number): string {
  const h = hour.toString().padStart(2, '0')
  const m = minute.toString().padStart(2, '0')
  return `${h}:${m}`
}

function normalize(input: string): string {
  return input
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[.,!?;]+$/g, '')
    .replace(/\bmidnight\b/g, '0:00')
}

type Matcher = {
  pattern: RegExp
  build: (m: RegExpMatchArray) => NlToCronResult | null
}

const MATCHERS: Matcher[] = [
  // ── Exact named patterns ──
  {
    pattern: /^every\s+minute|minutely|each\s+minute$/,
    build: () => ({ cron: '* * * * *', description: 'Every minute' }),
  },
  {
    pattern: /^every\s+hour|hourly|each\s+hour$/,
    build: () => ({ cron: '0 * * * *', description: 'At minute 0, every hour' }),
  },
  {
    pattern: /^(midnight|0:00)(\s+daily)?$/,
    build: () => ({ cron: '0 0 * * *', description: 'At midnight, every day' }),
  },
  {
    pattern: /^(daily|every\s+day)$/,
    build: () => ({ cron: '0 0 * * *', description: 'At midnight, every day' }),
  },
  {
    pattern: /^weekdays?$/,
    build: () => ({ cron: '0 0 * * 1-5', description: 'At midnight, Monday through Friday' }),
  },
  {
    pattern: /^weekends?$/,
    build: () => ({ cron: '0 0 * * 0,6', description: 'At midnight, Saturday and Sunday' }),
  },

  // ── Interval patterns ──
  {
    pattern: /^every\s+(\d+)\s+minutes?$/,
    build: (m) => {
      const n = parseInt(m[1], 10)
      if (n < 1 || n > 59) return null
      return { cron: `*/${n} * * * *`, description: `Every ${n} minutes` }
    },
  },
  {
    pattern: /^every\s+(\d+)\s+hours?$/,
    build: (m) => {
      const n = parseInt(m[1], 10)
      if (n < 1 || n > 23) return null
      return { cron: `0 */${n} * * *`, description: `Every ${n} hours` }
    },
  },

  // ── Day of week with time ──
  {
    pattern: /^every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sun|mon|tue|wed|thu|fri|sat|sunday)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/i,
    build: (m) => {
      const dayNum = DAY_MAP[m[1].toLowerCase()]
      if (dayNum === undefined) return null
      const t = parseTime(m[2], m[3], m[4])
      if (!t) return null
      const dayLabel = Object.entries(DAY_MAP).find(([, v]) => v === dayNum)?.[0] ?? ''
      return {
        cron: `${t.minute} ${t.hour} * * ${dayNum}`,
        description: `At ${formatTime(t.hour, t.minute)}, every ${dayLabel.charAt(0).toUpperCase() + dayLabel.slice(1)}`,
      }
    },
  },
  {
    pattern: /^every\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)$/i,
    build: (m) => {
      const dayNum = DAY_MAP[m[1].toLowerCase()]
      if (dayNum === undefined) return null
      const dayLabel = Object.entries(DAY_MAP).find(([, v]) => v === dayNum)?.[0] ?? ''
      return {
        cron: `0 0 * * ${dayNum}`,
        description: `At midnight, every ${dayLabel.charAt(0).toUpperCase() + dayLabel.slice(1)}`,
      }
    },
  },
  {
    pattern: /^(weekdays?|every\s+weekday)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/i,
    build: (m) => {
      const t = parseTime(m[2], m[3], m[4])
      if (!t) return null
      return {
        cron: `${t.minute} ${t.hour} * * 1-5`,
        description: `At ${formatTime(t.hour, t.minute)}, Monday through Friday`,
      }
    },
  },
  {
    pattern: /^(weekends?|every\s+weekend)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/i,
    build: (m) => {
      const t = parseTime(m[2], m[3], m[4])
      if (!t) return null
      return {
        cron: `${t.minute} ${t.hour} * * 0,6`,
        description: `At ${formatTime(t.hour, t.minute)}, Saturday and Sunday`,
      }
    },
  },

  // ── Daily with time ──
  {
    pattern: /^(every\s+day|daily)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$/i,
    build: (m) => {
      const t = parseTime(m[2], m[3], m[4])
      if (!t) return null
      return {
        cron: `${t.minute} ${t.hour} * * *`,
        description: `At ${formatTime(t.hour, t.minute)}, every day`,
      }
    },
  },
  {
    pattern: /^at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+(every\s+day|daily)$/i,
    build: (m) => {
      const t = parseTime(m[1], m[2], m[3])
      if (!t) return null
      return {
        cron: `${t.minute} ${t.hour} * * *`,
        description: `At ${formatTime(t.hour, t.minute)}, every day`,
      }
    },
  },

  // ── Monthly ──
  {
    pattern: /^monthly$/,
    build: () => ({ cron: '0 0 1 * *', description: 'On the 1st of every month' }),
  },
  {
    pattern: /^(monthly|every\s+month)\s+on\s+the\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?)?$/i,
    build: (m) => {
      const day = parseInt(m[2], 10)
      if (day < 1 || day > 31) return null
      if (m[3]) {
        const t = parseTime(m[3], m[4], m[5])
        if (!t) return null
        return {
          cron: `${t.minute} ${t.hour} ${day} * *`,
          description: `At ${formatTime(t.hour, t.minute)}, on day ${day} of the month`,
        }
      }
      return {
        cron: `0 0 ${day} * *`,
        description: `On day ${day} of the month`,
      }
    },
  },
]

/**
 * Convert natural language text to a cron expression.
 *
 * @param text - Natural language description (e.g. "every day at 9am")
 * @returns {NlToCronResult | null} Parsed result or null if unparseable
 */
export function nlToCron(text: string): NlToCronResult | null {
  const normalized = normalize(text)
  if (!normalized) return null

  for (const matcher of MATCHERS) {
    const match = normalized.match(matcher.pattern)
    if (match) {
      try {
        return matcher.build(match)
      } catch {
        continue
      }
    }
  }

  return null
}
