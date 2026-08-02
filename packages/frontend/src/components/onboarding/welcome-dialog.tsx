"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Sparkles, Trash2, ShieldCheck, BarChart3 } from "lucide-react"
import { useOnboarding } from "./onboarding-provider"

const features = [
  {
    icon: Trash2,
    title: "Submit Unlearning Requests",
    description:
      "Submit deletion requests with your choice of algorithm and track the entire unlearning pipeline.",
  },
  {
    icon: ShieldCheck,
    title: "Verify Deletions",
    description:
      "Each operation generates a cryptographically verifiable certificate with a Merkle proof of deletion.",
  },
  {
    icon: BarChart3,
    title: "Monitor Operations",
    description:
      "Real-time dashboards, system health monitoring, and compliance reporting at your fingertips.",
  },
]

export function WelcomeDialog() {
  const { showWelcome, startTour, dismissTour, closeWelcome } = useOnboarding()
  const [dontShowAgain, setDontShowAgain] = useState(false)

  function handleExplore() {
    if (dontShowAgain) {
      dismissTour()
    } else {
      closeWelcome()
    }
  }

  function handleTakeTour() {
    startTour()
  }

  return (
    <AnimatePresence>
      {showWelcome && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 backdrop-blur-sm p-4"
        >
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.96 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="w-full max-w-[480px] rounded-2xl border border-[var(--border-default)] bg-[var(--bg-surface-elevated)] shadow-[var(--shadow-lg)]"
          >
            <div className="px-6 pb-2 pt-8 text-center">
              <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand-soft)] text-[var(--brand)]">
                <Sparkles className="h-7 w-7" />
              </span>
              <h2 className="mt-4 text-xl font-semibold text-[var(--text-primary)]">
                Welcome to VeriUnlearn
              </h2>
              <p className="mt-2 text-sm leading-relaxed text-[var(--text-secondary)]">
                Your enterprise machine unlearning platform for AI governance and
                compliance. Manage deletion requests, verify proofs, and monitor
                your infrastructure — all in one place.
              </p>
            </div>

            <div className="space-y-3 px-6 py-6">
              {features.map((feature) => (
                <div
                  key={feature.title}
                  className="flex items-start gap-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 transition-colors hover:border-[var(--brand-border)]"
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--brand-soft)] text-[var(--brand)]">
                    <feature.icon className="h-[18px] w-[18px]" />
                  </span>
                  <div className="min-w-0">
                    <h4 className="text-[13px] font-semibold text-[var(--text-primary)]">
                      {feature.title}
                    </h4>
                    <p className="mt-0.5 text-[12px] leading-relaxed text-[var(--text-secondary)]">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3 border-t border-[var(--border-subtle)] px-6 py-4">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleTakeTour}
                  className="flex-1 rounded-xl bg-[var(--brand)] px-4 py-2.5 text-sm font-semibold text-[var(--text-on-brand)] shadow-[var(--shadow-sm)] transition-all hover:bg-[var(--brand-strong)] active:scale-[0.98]"
                >
                  Take the Tour
                </button>
                <button
                  onClick={handleExplore}
                  className="flex-1 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] transition-all hover:bg-[var(--bg-hover)] active:scale-[0.98]"
                >
                  Explore on My Own
                </button>
              </div>
              <label className="flex cursor-pointer items-center justify-center gap-2">
                <input
                  type="checkbox"
                  checked={dontShowAgain}
                  onChange={(e) => setDontShowAgain(e.target.checked)}
                  className="h-4 w-4 rounded border-[var(--border-default)] text-[var(--brand)] focus:ring-[var(--brand)]"
                />
                <span className="text-[12px] text-[var(--text-tertiary)]">
                  Don&apos;t show this again
                </span>
              </label>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
