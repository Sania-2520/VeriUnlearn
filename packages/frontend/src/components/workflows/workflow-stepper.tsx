"use client"

import { clsx } from "clsx"
import { Check, X } from "lucide-react"
import { useWorkflow } from "./workflow-context"

const stepIcon = (state: string) => {
  if (state === "completed") return <Check className="h-3.5 w-3.5" />
  if (state === "error") return <X className="h-3.5 w-3.5" />
  return null
}

const stepCircleClass = (state: string, isClickable: boolean) =>
  clsx(
    "relative z-10 flex h-8 w-8 items-center justify-center rounded-full border-2 text-xs font-semibold transition-all duration-300",
    {
      "border-[var(--brand)] bg-[var(--brand)] text-[var(--text-on-brand)] shadow-[0_0_0_4px_var(--brand-soft)]": state === "current",
      "border-[var(--success)] bg-[var(--success)] text-white": state === "completed",
      "border-[var(--danger)] bg-[var(--danger)] text-white": state === "error",
      "border-[var(--border-strong)] bg-[var(--bg-surface)] text-[var(--text-tertiary)]": state === "pending",
      "cursor-pointer hover:border-[var(--brand)] hover:bg-[var(--brand-soft)] hover:text-[var(--brand-strong)]": isClickable,
    },
  )

export function WorkflowStepper({ className }: { className?: string }) {
  const { steps, currentStep, stepStates, goToStep } = useWorkflow()

  return (
    <nav aria-label="Workflow progress" className={className}>
      <ol className="flex items-center">
        {steps.map((step, index) => {
          const state = stepStates[index]
          const isClickable = state === "completed" || state === "error"

          return (
            <li key={step.id} className="flex items-center flex-1 last:flex-none">
              <button
                type="button"
                onClick={() => isClickable && goToStep(index)}
                disabled={!isClickable}
                className={clsx(
                  "flex flex-col items-center gap-1.5 transition-all",
                  isClickable ? "cursor-pointer" : "cursor-default",
                )}
                aria-current={state === "current" ? "step" : undefined}
                aria-label={`${step.title}${state === "completed" ? " (completed)" : ""}${state === "error" ? " (error)" : ""}`}
              >
                <div className={stepCircleClass(state, isClickable)}>
                  {stepIcon(state) ?? (
                    <span className={state === "current" ? "text-[var(--text-on-brand)]" : ""}>{index + 1}</span>
                  )}
                </div>
                <span
                  className={clsx(
                    "hidden text-xs font-medium transition-colors sm:block",
                    state === "current" && "text-[var(--brand-strong)]",
                    state === "completed" && "text-[var(--success)]",
                    state === "error" && "text-[var(--danger)]",
                    state === "pending" && "text-[var(--text-tertiary)]",
                  )}
                >
                  {step.title}
                </span>
              </button>

              {index < steps.length - 1 && (
                <div
                  className={clsx(
                    "mx-2 flex-1 h-px transition-colors duration-300 sm:mx-3",
                    index < currentStep
                      ? "bg-[var(--success)]"
                      : "bg-[var(--border-default)]",
                  )}
                  aria-hidden
                />
              )}
            </li>
          )
        })}
      </ol>

      <p className="mt-3 text-center text-xs text-[var(--text-tertiary)] sm:hidden">
        Step {currentStep + 1} of {steps.length} &mdash; {steps[currentStep]?.title}
      </p>
    </nav>
  )
}
