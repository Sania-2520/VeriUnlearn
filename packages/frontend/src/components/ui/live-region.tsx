"use client"

import { useState, useEffect, useRef, type ReactNode } from "react"

interface LiveRegionProps {
  children?: ReactNode
  message?: string
  mode?: "polite" | "assertive"
  debounceMs?: number
  className?: string
}

export function LiveRegion({
  children,
  message,
  mode = "polite",
  debounceMs = 300,
  className,
}: LiveRegionProps) {
  const [announcement, setAnnouncement] = useState("")
  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => {
    if (message === undefined) return

    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current)
    }

    debounceTimer.current = setTimeout(() => {
      setAnnouncement(message)
    }, debounceMs)

    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current)
      }
    }
  }, [message, debounceMs])

  return (
    <>
      <div
        aria-live={mode}
        aria-atomic="true"
        className="sr-only"
      >
        {announcement}
      </div>
      {children && (
        <div
          aria-live={mode === "assertive" ? "assertive" : "polite"}
          aria-atomic="false"
          className={className}
        >
          {children}
        </div>
      )}
    </>
  )
}
