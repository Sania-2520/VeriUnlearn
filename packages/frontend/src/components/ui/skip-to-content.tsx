"use client"

import { motion } from "framer-motion"
import { clsx } from "clsx"

export function SkipToContent() {
  return (
    <motion.a
      href="#main-content"
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={clsx(
        "sr-only z-[100] rounded-lg px-4 py-2.5 text-sm font-semibold shadow-lg",
        "focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:outline-none",
        "bg-[var(--brand)] text-[var(--text-on-brand)]",
        "focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-app)]",
        "dark:focus-visible:ring-[var(--accent-500)]",
      )}
      onClick={(e) => {
        e.preventDefault()
        const el = document.getElementById("main-content")
        if (el) {
          el.setAttribute("tabindex", "-1")
          el.focus({ preventScroll: true })
          el.scrollIntoView({ behavior: "smooth", block: "start" })
        }
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault()
          const el = document.getElementById("main-content")
          if (el) {
            el.setAttribute("tabindex", "-1")
            el.focus({ preventScroll: true })
            el.scrollIntoView({ behavior: "smooth", block: "start" })
          }
        }
      }}
    >
      Skip to content
    </motion.a>
  )
}
