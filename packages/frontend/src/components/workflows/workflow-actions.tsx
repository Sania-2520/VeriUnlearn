"use client"

import { ArrowLeft, ArrowRight, Check, SkipForward, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useWorkflow } from "./workflow-context"

export function WorkflowActions({
  onCancel,
  onComplete,
  nextLabel,
  completeLabel,
  showSkip,
  onSkip,
  className,
}: {
  onCancel?: () => void
  onComplete?: () => void
  nextLabel?: string
  completeLabel?: string
  showSkip?: boolean
  onSkip?: () => void
  className?: string
}) {
  const {
    isFirstStep,
    isLastStep,
    previousStep,
    nextStep,
    isSubmitting,
    validationMap,
    currentStep,
    steps,
  } = useWorkflow()

  const stepValidation = validationMap.get(currentStep)
  const canProceed = stepValidation ? stepValidation.isValid : true
  const step = steps[currentStep]

  return (
    <div className={className}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {!isFirstStep && (
            <Button
              type="button"
              variant="outline"
              size="md"
              onClick={previousStep}
              disabled={isSubmitting}
            >
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
          )}

          {onCancel && (
            <Button
              type="button"
              variant="ghost"
              size="md"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              <X className="h-4 w-4" />
              Cancel
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {showSkip && step?.optional && (
            <Button
              type="button"
              variant="ghost"
              size="md"
              onClick={onSkip}
              disabled={isSubmitting}
            >
              <SkipForward className="h-4 w-4" />
              Skip
            </Button>
          )}

          {!isLastStep ? (
            <Button
              type="button"
              size="md"
              onClick={nextStep}
              disabled={!canProceed || isSubmitting}
            >
              {nextLabel ?? "Next"}
              <ArrowRight className="h-4 w-4" />
            </Button>
          ) : (
            <Button
              type="button"
              size="md"
              loading={isSubmitting}
              disabled={!canProceed}
              onClick={onComplete}
            >
              <Check className="h-4 w-4" />
              {completeLabel ?? "Submit"}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
