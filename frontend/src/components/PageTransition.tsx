import { AnimatePresence, motion } from 'framer-motion'
import type { ReactNode } from 'react'
import type { MotionSpeed } from '@/types/motion'

const OPACITY_DURATION_BY_SPEED: Record<MotionSpeed, number> = {
  fast: 0.24,
  normal: 0.4,
  slow: 0.6,
}

interface PageTransitionProps {
  children: ReactNode
  pathname: string
  speed: MotionSpeed
}

export default function PageTransition({ children, pathname, speed }: PageTransitionProps) {
  return (
    <AnimatePresence mode="popLayout">
      <motion.div
        key={pathname}
        data-page-transition={pathname}
        data-motion-speed={speed}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{
          opacity: { duration: OPACITY_DURATION_BY_SPEED[speed], ease: 'easeInOut' },
        }}
        style={{
          position: 'relative',
          zIndex: 1,
          width: '100%',
          minHeight: 'calc(100vh - 152px)',
          willChange: 'opacity',
        }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  )
}
