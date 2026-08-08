"use client"

import { useEffect, useRef, useState, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useOnboarding } from "./onboarding-provider"
import type { TourStep } from "./tour-step"
import {
  Sparkles,
  LayoutDashboard,
  ListTodo,
  BarChart3,
  ShieldCheck,
  Gauge,
  Bot,
  Rocket,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"
import { clsx } from "clsx"

const ARROW_SIZE = 10
const TOOLTIP_GAP = 16

const iconMap: Record<string, React.ComponentType<{ className?: string }>> = {
  Sparkles,
  LayoutDashboard,
  ListTodo,
  BarChart3,
  ShieldCheck,
  Gauge,
  Bot,
  Rocket,
}

function getIcon(name?: string) {
  if (!name) return null
  const Icon = iconMap[name]
  return Icon ? <Icon className="h-5 w-5" /> : null
}

function getTooltipStyle(
  rect: DOMRect | null,
  placement: TourStep["placement"],
  tooltipWidth: number,
  tooltipHeight: number,
): React.CSSProperties {
  if (!rect || placement === "center") {
    return { top: "50%", left: "50%", transform: "translate(-50%,-50%)" }
  }

  const gap = ARROW_SIZE + TOOLTIP_GAP
  let top = 0
  let left = 0

  switch (placement) {
    case "top":
      top = rect.top - tooltipHeight - gap
      left = rect.left + rect.width / 2 - tooltipWidth / 2
      break
    case "bottom":
      top = rect.bottom + gap
      left = rect.left + rect.width / 2 - tooltipWidth / 2
      break
    case "left":
      top = rect.top + rect.height / 2 - tooltipHeight / 2
      left = rect.left - tooltipWidth - gap
      break
    case "right":
      top = rect.top + rect.height / 2 - tooltipHeight / 2
      left = rect.right + gap
      break
  }

  const margin = 16
  const vw = window.innerWidth
  const vh = window.innerHeight
  left = Math.max(margin, Math.min(left, vw - tooltipWidth - margin))
  top = Math.max(margin, Math.min(top, vh - tooltipHeight - margin))

  return { top: `${top}px`, left: `${left}px` }
}

function CutoutSVG({ rect }: { rect: DOMRect }) {
  const p = 8
  const x = rect.left - p
  const y = rect.top - p
  const w = rect.width + p * 2
  const h = rect.height + p * 2

  return (
    <svg
      className="fixed inset-0 z-40 h-full w-full"
      aria-hidden="true"
      style={{ pointerEvents: "none" }}
    >
      <defs>
        <mask id="tour-cutout">
          <rect width="100%" height="100%" fill="white" />
          <rect x={x} y={y} width={w} height={h} fill="black" rx="10" />
        </mask>
      </defs>
      <rect
        width="100%"
        height="100%"
        fill="rgba(0,0,0,0.55)"
        mask="url(#tour-cutout)"
        style={{ backdropFilter: "blur(1px)" }}
      />
    </svg>
  )
}

function PulseRing({ rect }: { rect: DOMRect }) {
  const p = 8
  return (
    <div
      className="fixed z-40 rounded-[10px] border-2 border-[var(--brand)]"
      style={{
        left: rect.left - p,
        top: rect.top - p,
        width: rect.width + p * 2,
        height: rect.height + p * 2,
        pointerEvents: "none",
        boxShadow: "0 0 0 2px color-mix(in srgb, var(--brand) 30%, transparent), 0 0 20px color-mix(in srgb, var(--brand) 15%, transparent)",
        animation: "vu-tour-pulse 2s cubic-bezier(0.4,0,0.6,1) infinite",
      }}
    />
  )
}

function TourTooltip({
  step,
  stepNumber,
  totalSteps,
  onNext,
  onPrev,
  onSkip,
  onAction,
  onDismiss,
}: {
  step: TourStep
  stepNumber: number
  totalSteps: number
  onNext: () => void
  onPrev: () => void
  onSkip: () => void
  onAction: () => void
  onDismiss: () => void
}) {
  const isFirst = stepNumber === 0
  const isLast = stepNumber === totalSteps - 1

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -10, scale: 0.96 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className="w-[calc(100vw-32px)] min-w-[300px] max-w-[400px] rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] shadow-[var(--shadow-lg)]"
      style={{ pointerEvents: "auto" }}
    >
      <div className="flex items-center justify-between px-5 pb-2 pt-5">
        <div className="flex items-center gap-2.5">
          {step.icon && (
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--brand-soft)] text-[var(--brand)]">
              {getIcon(step.icon)}
            </span>
          )}
          <span className="text-[12px] font-medium tracking-wide text-[var(--text-tertiary)]">
            {stepNumber + 1} / {totalSteps}
          </span>
        </div>
        <button
          onClick={onDismiss}
          className="flex h-7 w-7 items-center justify-center rounded-lg text-[var(--text-tertiary)] transition-colors hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)]"
          aria-label="Close tour"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="px-5 pb-4 pt-1">
        <h3 className="text-[16px] font-semibold leading-snug text-[var(--text-primary)]">
          {step.title}
        </h3>
        <p className="mt-2 text-[13px] leading-relaxed text-[var(--text-secondary)]">
          {step.content}
        </p>
      </div>

      {step.showDots && (
        <div className="flex items-center justify-center gap-1.5 px-5 pb-4">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={clsx(
                "h-1.5 rounded-full transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
                i === stepNumber
                  ? "w-5 bg-[var(--brand)]"
                  : "w-1.5 bg-[var(--border-strong)]",
              )}
            />
          ))}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-[var(--border-subtle)] px-5 py-3.5">
        {step.showSkip && !isLast ? (
          <button
            onClick={onSkip}
            className="text-[12px] font-medium text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
          >
            Skip tour
          </button>
        ) : isFirst ? (
          <button
            onClick={onSkip}
            className="text-[12px] font-medium text-[var(--text-tertiary)] transition-colors hover:text-[var(--text-primary)]"
          >
            Skip tour
          </button>
        ) : (
          <div />
        )}

        <div className="flex items-center gap-2">
          {!isFirst && !step.action && (
            <button
              onClick={onPrev}
              className="inline-flex items-center gap-1 rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 py-1.5 text-[12px] font-medium text-[var(--text-secondary)] transition-all hover:bg-[var(--bg-hover)] hover:text-[var(--text-primary)] active:scale-[0.98]"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Back
            </button>
          )}

          {step.action ? (
            <button
              onClick={onAction}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--brand)] px-4 py-1.5 text-[13px] font-semibold text-[var(--text-on-brand)] shadow-[var(--shadow-sm)] transition-all hover:bg-[var(--brand-strong)] active:scale-[0.98]"
            >
              {step.action.label}
            </button>
          ) : isLast ? (
            <button
              onClick={onNext}
              className="inline-flex items-center gap-1.5 rounded-lg bg-[var(--brand)] px-4 py-1.5 text-[13px] font-semibold text-[var(--text-on-brand)] shadow-[var(--shadow-sm)] transition-all hover:bg-[var(--brand-strong)] active:scale-[0.98]"
            >
              Finish
            </button>
          ) : (
            <button
              onClick={onNext}
              className="inline-flex items-center gap-1 rounded-lg bg-[var(--brand)] px-4 py-1.5 text-[13px] font-semibold text-[var(--text-on-brand)] shadow-[var(--shadow-sm)] transition-all hover:bg-[var(--brand-strong)] active:scale-[0.98]"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export function TourOverlay() {
  const {
    isActive,
    currentStep,
    tourSteps,
    nextStep,
    prevStep,
    endTour,
    dismissTour,
  } = useOnboarding()

  const step = tourSteps[currentStep]
  const [targetRect, setTargetRect] = useState<DOMRect | null>(null)
  const [tooltipSize, setTooltipSize] = useState({ w: 380, h: 280 })
  const tooltipRef = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  const measure = useCallback(() => {
    if (tooltipRef.current) {
      const r = tooltipRef.current.getBoundingClientRect()
      if (r.width > 0 && r.height > 0) {
        setTooltipSize({ w: r.width, h: r.height })
      }
    }
  }, [])

  const updateRect = useCallback(() => {
    if (!step || step.placement === "center") {
      setTargetRect(null)
      return
    }
    const el = document.querySelector(step.targetSelector)
    setTargetRect(el ? el.getBoundingClientRect() : null)
  }, [step])

  useEffect(() => {
    if (!isActive) { setVisible(false); return }
    setVisible(true)
  }, [isActive])

  useEffect(() => {
    if (!visible || !step) return

    setTargetRect(null)
    setTooltipSize({ w: 380, h: 280 })

    if (step.placement !== "center") {
      const el = document.querySelector(step.targetSelector)
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" })
        const t1 = setTimeout(() => {
          updateRect()
          const t2 = setTimeout(measure, 80)
          return () => clearTimeout(t2)
        }, 450)
        return () => clearTimeout(t1)
      }
    } else {
      setTimeout(measure, 50)
    }
  }, [visible, step, updateRect, measure])

  useEffect(() => {
    if (!visible || !step || step.placement === "center") return

    const onScroll = () => updateRect()
    const onResize = () => { updateRect(); measure() }

    window.addEventListener("scroll", onScroll, { passive: true, capture: true })
    window.addEventListener("resize", onResize)
    return () => {
      window.removeEventListener("scroll", onScroll, { capture: true } as EventListenerOptions)
      window.removeEventListener("resize", onResize)
    }
  }, [visible, step, updateRect, measure])

  useEffect(() => {
    if (!visible) return
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") { dismissTour(); return }
      if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); nextStep(); return }
      if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); if (currentStep > 0) prevStep(); return }
    }
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [visible, currentStep, nextStep, prevStep, dismissTour])

  const handleAction = useCallback(() => {
    const s = tourSteps[currentStep]
    if (s?.action?.href) {
      endTour()
      window.location.href = s.action.href
    } else if (s?.action?.onClick) {
      s.action.onClick()
      nextStep()
    } else {
      nextStep()
    }
  }, [currentStep, tourSteps, nextStep, endTour])

  if (!visible || !step) return null

  const isCenter = step.placement === "center"
  const tooltipStyle = getTooltipStyle(isCenter ? null : targetRect, step.placement, tooltipSize.w, tooltipSize.h)

  const tooltipEl = (
    <div ref={tooltipRef}>
      <TourTooltip
        step={step}
        stepNumber={currentStep}
        totalSteps={tourSteps.length}
        onNext={nextStep}
        onPrev={prevStep}
        onSkip={dismissTour}
        onAction={handleAction}
        onDismiss={dismissTour}
      />
    </div>
  )

  return (
    <AnimatePresence>
      <motion.div
        key="tour-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.25 }}
        className="fixed inset-0 z-50"
      >
        {isCenter ? (
          <div className="flex h-full w-full items-center justify-center bg-black/55 backdrop-blur-sm">
            {tooltipEl}
          </div>
        ) : (
          <>
            {targetRect && <CutoutSVG rect={targetRect} />}
            {targetRect && <PulseRing rect={targetRect} />}
            {targetRect && (
              <div className="fixed z-50" style={tooltipStyle}>
                {tooltipEl}
              </div>
            )}
          </>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
