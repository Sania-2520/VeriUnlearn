"use client"

import { useState, useEffect, useRef } from "react"
import { debounce } from "@/lib/utils/performance"

interface ViewportSize {
  width: number
  height: number
}

export function useViewportSize(debounceMs = 200): ViewportSize {
  const [size, setSize] = useState<ViewportSize>({ width: 0, height: 0 })
  const hydrated = useRef(false)

  useEffect(() => {
    if (!hydrated.current) {
      hydrated.current = true
      setSize({ width: window.innerWidth, height: window.innerHeight })
    }

    const debouncedSetSize = debounce(() => {
      setSize({ width: window.innerWidth, height: window.innerHeight })
    }, debounceMs)

    window.addEventListener("resize", debouncedSetSize)
    return () => window.removeEventListener("resize", debouncedSetSize)
  }, [debounceMs])

  return size
}
