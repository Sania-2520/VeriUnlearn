"use client"

import { useEffect, useRef, useCallback } from "react"

type ModifierKey = "ctrl" | "meta" | "shift" | "alt"

interface KeyboardShortcutOptions {
  key: string
  modifiers?: ModifierKey[]
  handler: (e: KeyboardEvent) => void
  preventDefault?: boolean
  scopeRef?: React.RefObject<HTMLElement | null>
  enabled?: boolean
}

function matchModifiers(e: KeyboardEvent, modifiers: ModifierKey[]): boolean {
  const state: Record<ModifierKey, boolean> = {
    ctrl: e.ctrlKey,
    meta: e.metaKey,
    shift: e.shiftKey,
    alt: e.altKey,
  }

  const required = new Set(modifiers)
  const active = (Object.keys(state) as ModifierKey[]).filter(
    (k) => state[k],
  )

  if (required.size !== active.length) return false
  return required.size === active.length
}

export function useKeyboardShortcut({
  key,
  modifiers = [],
  handler,
  preventDefault = true,
  scopeRef,
  enabled = true,
}: KeyboardShortcutOptions) {
  const handlerRef = useRef(handler)
  handlerRef.current = handler

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (!enabled) return

      if (e.key.toLowerCase() !== key.toLowerCase()) return
      if (!matchModifiers(e, modifiers)) return

      if (scopeRef?.current) {
        if (!scopeRef.current.contains(e.target as Node)) return
      }

      if (preventDefault) {
        e.preventDefault()
        e.stopPropagation()
      }

      handlerRef.current(e)
    },
    [key, modifiers, preventDefault, scopeRef, enabled],
  )

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown, true)
    return () => document.removeEventListener("keydown", handleKeyDown, true)
  }, [handleKeyDown])
}
