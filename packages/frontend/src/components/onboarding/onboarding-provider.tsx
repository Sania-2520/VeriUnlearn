"use client"

import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react"
import type { ReactNode } from "react"
import type { TourStep } from "./tour-step"
import { defaultTourSteps } from "./tour-config"

const STORAGE_KEYS = {
  DISMISSED: "vu-tour-dismissed",
  COMPLETED: "vu-tour-completed",
  STEP: "vu-tour-step",
} as const

interface OnboardingState {
  currentStep: number
  isActive: boolean
  showWelcome: boolean
  isDismissed: boolean
  isCompleted: boolean
}

interface OnboardingContextType extends OnboardingState {
  tourSteps: TourStep[]
  startTour: () => void
  nextStep: () => void
  prevStep: () => void
  goToStep: (index: number) => void
  endTour: () => void
  dismissTour: () => void
  resetTour: () => void
  closeWelcome: () => void
}

const OnboardingContext = createContext<OnboardingContextType | null>(null)

export function useOnboarding() {
  const ctx = useContext(OnboardingContext)
  if (!ctx) {
    throw new Error("useOnboarding must be used within OnboardingProvider")
  }
  return ctx
}

export function OnboardingProvider({
  children,
  steps = defaultTourSteps,
}: {
  children: ReactNode
  steps?: TourStep[]
}) {
  const [state, setState] = useState<OnboardingState>({
    currentStep: 0,
    isActive: false,
    showWelcome: false,
    isDismissed: false,
    isCompleted: false,
  })
  const initRef = useRef(false)

  useEffect(() => {
    if (initRef.current) return
    initRef.current = true

    const dismissed = localStorage.getItem(STORAGE_KEYS.DISMISSED) === "true"
    const completed = localStorage.getItem(STORAGE_KEYS.COMPLETED) === "true"

    if (dismissed || completed) {
      setState((prev) => ({
        ...prev,
        isDismissed: dismissed,
        isCompleted: completed,
      }))
      return
    }

    const timer = setTimeout(() => {
      setState((prev) => ({
        ...prev,
        showWelcome: true,
      }))
    }, 500)

    return () => clearTimeout(timer)
  }, [])

  const startTour = useCallback(() => {
    setState((prev) => ({
      ...prev,
      isActive: true,
      showWelcome: false,
      currentStep: 0,
    }))
  }, [])

  const nextStep = useCallback(() => {
    setState((prev) => {
      const next = prev.currentStep + 1
      if (next >= steps.length) {
        localStorage.setItem(STORAGE_KEYS.COMPLETED, "true")
        return { ...prev, isActive: false, isCompleted: true }
      }
      localStorage.setItem(STORAGE_KEYS.STEP, String(next))
      return { ...prev, currentStep: next }
    })
  }, [steps.length])

  const prevStep = useCallback(() => {
    setState((prev) => {
      const prevStep = Math.max(0, prev.currentStep - 1)
      localStorage.setItem(STORAGE_KEYS.STEP, String(prevStep))
      return { ...prev, currentStep: prevStep }
    })
  }, [])

  const goToStep = useCallback((index: number) => {
    setState((prev) => {
      const clamped = Math.max(0, Math.min(index, steps.length - 1))
      localStorage.setItem(STORAGE_KEYS.STEP, String(clamped))
      return { ...prev, currentStep: clamped }
    })
  }, [steps.length])

  const endTour = useCallback(() => {
    localStorage.setItem(STORAGE_KEYS.COMPLETED, "true")
    setState((prev) => ({ ...prev, isActive: false, isCompleted: true }))
  }, [])

  const dismissTour = useCallback(() => {
    localStorage.setItem(STORAGE_KEYS.DISMISSED, "true")
    setState((prev) => ({
      ...prev,
      isActive: false,
      showWelcome: false,
      isDismissed: true,
    }))
  }, [])

  const closeWelcome = useCallback(() => {
    setState((prev) => ({ ...prev, showWelcome: false }))
  }, [])

  const resetTour = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.DISMISSED)
    localStorage.removeItem(STORAGE_KEYS.COMPLETED)
    localStorage.removeItem(STORAGE_KEYS.STEP)
    setState({
      currentStep: 0,
      isActive: false,
      showWelcome: false,
      isDismissed: false,
      isCompleted: false,
    })
  }, [])

  const value = useMemo(
    () => ({
      ...state,
      tourSteps: steps,
      startTour,
      nextStep,
      prevStep,
      goToStep,
      endTour,
      dismissTour,
      resetTour,
      closeWelcome,
    }),
    [state, steps, startTour, nextStep, prevStep, goToStep, endTour, dismissTour, resetTour, closeWelcome],
  )

  return (
    <OnboardingContext.Provider value={value}>
      {children}
    </OnboardingContext.Provider>
  )
}
