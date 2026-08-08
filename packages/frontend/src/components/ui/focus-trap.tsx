"use client"

import {
  useRef,
  useEffect,
  useCallback,
  forwardRef,
  useImperativeHandle,
  type ReactNode,
} from "react"

export interface FocusTrapHandle {
  focus: (options?: FocusOptions) => void
}

interface FocusTrapProps {
  children: ReactNode
  active?: boolean
  initialFocusRef?: React.RefObject<HTMLElement | null>
  restoreFocus?: boolean
  restoreFocusRef?: React.RefObject<HTMLElement | null>
}

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "textarea:not([disabled])",
  "select:not([disabled])",
  "details",
  "[tabindex]:not([tabindex='-1'])",
].join(", ")

export const FocusTrap = forwardRef<FocusTrapHandle, FocusTrapProps>(
  (
    {
      children,
      active = true,
      initialFocusRef,
      restoreFocus = true,
      restoreFocusRef,
    },
    ref,
  ) => {
    const containerRef = useRef<HTMLDivElement>(null)
    const previousActiveElement = useRef<Element | null>(null)

    const getFocusableElements = useCallback(() => {
      if (!containerRef.current) return []
      return Array.from(
        containerRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      )
    }, [])

    const focusInitial = useCallback(() => {
      if (initialFocusRef?.current) {
        initialFocusRef.current.focus()
        return
      }
      const focusable = getFocusableElements()
      if (focusable.length > 0) {
        focusable[0].focus()
      }
    }, [initialFocusRef, getFocusableElements])

    useImperativeHandle(
      ref,
      () => ({
        focus: (options?: FocusOptions) => {
          focusInitial()
          if (options) {
            const el = containerRef.current?.querySelector<HTMLElement>(
              FOCUSABLE_SELECTOR,
            )
            el?.focus(options)
          }
        },
      }),
      [focusInitial],
    )

    useEffect(() => {
      if (!active) return

      previousActiveElement.current = document.activeElement
      // Capture the restore target once at effect setup so the cleanup runs
      // against the same element even if the ref is reassigned later.
      const restoreTarget = restoreFocusRef?.current

      requestAnimationFrame(() => {
        focusInitial()
      })

      return () => {
        if (restoreFocus) {
          const target = restoreTarget ?? previousActiveElement.current
          if (target instanceof HTMLElement) {
            target.focus({ preventScroll: true })
          }
        }
      }
    }, [active, focusInitial, restoreFocus, restoreFocusRef])

    useEffect(() => {
      if (!active) return

      const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key !== "Tab") return

        const focusable = getFocusableElements()
        if (focusable.length === 0) {
          e.preventDefault()
          return
        }

        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        const current = document.activeElement

        if (e.shiftKey) {
          if (current === first || !focusable.includes(current as HTMLElement)) {
            e.preventDefault()
            last.focus()
          }
        } else {
          if (current === last || !focusable.includes(current as HTMLElement)) {
            e.preventDefault()
            first.focus()
          }
        }
      }

      document.addEventListener("keydown", handleKeyDown, true)
      return () => document.removeEventListener("keydown", handleKeyDown, true)
    }, [active, getFocusableElements])

    return (
      <div ref={containerRef} data-focus-trap="">
        {children}
      </div>
    )
  },
)
FocusTrap.displayName = "FocusTrap"
