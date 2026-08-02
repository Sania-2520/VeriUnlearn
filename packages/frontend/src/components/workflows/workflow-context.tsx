"use client"

import { createContext, useContext, useState, useCallback, useRef, useEffect } from "react"
import { AnimatePresence } from "framer-motion"

export type StepState = "pending" | "current" | "completed" | "error"

export interface Step {
  id: string
  title: string
  description?: string
  optional?: boolean
}

export interface WorkflowValidation {
  isValid: boolean
  message?: string
}

interface WorkflowContextValue {
  steps: Step[]
  currentStep: number
  totalSteps: number
  direction: number
  stepStates: StepState[]
  formData: Record<string, unknown>
  goToStep: (index: number) => void
  nextStep: () => Promise<void>
  previousStep: () => void
  setStepValidation: (index: number, validation: WorkflowValidation) => void
  updateFormData: (data: Record<string, unknown>) => void
  resetWorkflow: () => void
  isFirstStep: boolean
  isLastStep: boolean
  isSubmitting: boolean
  setIsSubmitting: (v: boolean) => void
  validationMap: Map<number, WorkflowValidation>
}

const WorkflowContext = createContext<WorkflowContextValue | null>(null)

export function useWorkflow() {
  const ctx = useContext(WorkflowContext)
  if (!ctx) throw new Error("useWorkflow must be used within a WorkflowProvider")
  return ctx
}

export function WorkflowProvider({
  steps,
  onComplete,
  children,
  initialData,
}: {
  steps: Step[]
  onComplete?: (data: Record<string, unknown>) => Promise<void>
  children: React.ReactNode
  initialData?: Record<string, unknown>
}) {
  const [currentStep, setCurrentStep] = useState(0)
  const [direction, setDirection] = useState(1)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState<Record<string, unknown>>(initialData ?? {})
  const [validationMap, setValidationMap] = useState<Map<number, WorkflowValidation>>(new Map())
  const validationRefs = useRef<Map<number, WorkflowValidation>>(new Map())

  const stepStates: StepState[] = steps.map((_, i) => {
    if (i === currentStep) return "current"
    if (i < currentStep) return "completed"
    return "pending"
  })

  const updateFormData = useCallback((data: Record<string, unknown>) => {
    setFormData((prev) => ({ ...prev, ...data }))
  }, [])

  const setStepValidation = useCallback((index: number, validation: WorkflowValidation) => {
    validationRefs.current.set(index, validation)
    setValidationMap(new Map(validationRefs.current))
  }, [])

  const goToStep = useCallback(
    (index: number) => {
      if (index < 0 || index >= steps.length) return
      if (index > currentStep) {
        const prevValid = validationRefs.current.get(currentStep)
        if (prevValid && !prevValid.isValid) return
      }
      setDirection(index > currentStep ? 1 : -1)
      setCurrentStep(index)
    },
    [currentStep, steps.length],
  )

  const nextStep = useCallback(async () => {
    const validation = validationRefs.current.get(currentStep)
    if (validation && !validation.isValid) return

    if (currentStep < steps.length - 1) {
      setDirection(1)
      setCurrentStep((prev) => prev + 1)
    }
  }, [currentStep, steps.length])

  const previousStep = useCallback(() => {
    if (currentStep > 0) {
      setDirection(-1)
      setCurrentStep((prev) => prev - 1)
    }
  }, [currentStep])

  const resetWorkflow = useCallback(() => {
    setCurrentStep(0)
    setDirection(1)
    setFormData(initialData ?? {})
    validationRefs.current = new Map()
    setValidationMap(new Map())
    setIsSubmitting(false)
  }, [initialData])

  useEffect(() => {
    setDirection(1)
  }, [])

  const isFirstStep = currentStep === 0
  const isLastStep = currentStep === steps.length - 1

  return (
    <WorkflowContext.Provider
      value={{
        steps,
        currentStep,
        totalSteps: steps.length,
        direction,
        stepStates,
        formData,
        goToStep,
        nextStep,
        previousStep,
        setStepValidation,
        updateFormData,
        resetWorkflow,
        isFirstStep,
        isLastStep,
        isSubmitting,
        setIsSubmitting,
        validationMap,
      }}
    >
      <AnimatePresence mode="wait">{children}</AnimatePresence>
    </WorkflowContext.Provider>
  )
}
