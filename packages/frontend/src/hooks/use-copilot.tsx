"use client"

import { createContext, useContext, useEffect, useRef, useState, useCallback, type ReactNode } from "react"

interface CopilotContextType {
  isOpen: boolean
  open: () => void
  close: () => void
  toggle: () => void
}

const CopilotContext = createContext<CopilotContextType | undefined>(undefined)

export function CopilotProvider({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false)
  const isOpenRef = useRef(isOpen)
  isOpenRef.current = isOpen

  const open = useCallback(() => setIsOpen(true), [])
  const close = useCallback(() => setIsOpen(false), [])
  const toggle = useCallback(() => setIsOpen((prev) => !prev), [])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        e.stopPropagation()
        toggle()
      }
      if (e.key === "Escape" && isOpenRef.current) {
        e.preventDefault()
        close()
      }
    }
    document.addEventListener("keydown", handleKeyDown)
    return () => document.removeEventListener("keydown", handleKeyDown)
  }, [toggle, close])

  return (
    <CopilotContext.Provider value={{ isOpen, open, close, toggle }}>
      {children}
    </CopilotContext.Provider>
  )
}

export function useCopilot() {
  const ctx = useContext(CopilotContext)
  if (!ctx) throw new Error("useCopilot must be used within CopilotProvider")
  return ctx
}
