import { useMemo } from 'react'
import { useReducedMotion } from 'framer-motion'
import type { Variants } from 'framer-motion'

export interface StaggerVariants {
  container: Variants
  item: Variants
}

export function getStaggerVariants(
  delayChildren = 0.05,
  staggerChildren = 0.05,
): StaggerVariants {
  return {
    container: {
      hidden: { opacity: 1 },
      show: {
        opacity: 1,
        transition: {
          delayChildren,
          staggerChildren,
        },
      },
    },
    item: {
      hidden: { opacity: 0, y: 12 },
      show: {
        opacity: 1,
        y: 0,
        transition: {
          type: 'spring',
          stiffness: 300,
          damping: 20,
        },
      },
    },
  }
}

const REDUCED_MOTION_VARIANTS: StaggerVariants = {
  container: {
    hidden: { opacity: 1 },
    show: { opacity: 1 },
  },
  item: {
    hidden: { opacity: 1, y: 0 },
    show: { opacity: 1, y: 0 },
  },
}

export function useStaggerAnimation(
  delayChildren = 0.05,
  staggerChildren = 0.05,
): StaggerVariants {
  const prefersReducedMotion = useReducedMotion()

  return useMemo(
    () =>
      prefersReducedMotion
        ? REDUCED_MOTION_VARIANTS
        : getStaggerVariants(delayChildren, staggerChildren),
    [delayChildren, prefersReducedMotion, staggerChildren],
  )
}
