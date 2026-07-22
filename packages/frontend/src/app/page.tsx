"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useAuthStore } from "@/lib/store/auth-store"
import {
  Send,
  ArrowRight,
  ShieldCheck,
  Zap,
} from "lucide-react"

export default function Home() {
  const router = useRouter()
  const { isAuthenticated, loadUser, isLoading } = useAuthStore()
  const [prompt, setPrompt] = useState("")

  useEffect(() => {
    loadUser()
  }, [loadUser])

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.push("/dashboard")
    }
  }, [isLoading, isAuthenticated, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg-app)]">
        <div className="animate-spin h-8 w-8 border-4 border-[var(--brand)] border-t-transparent rounded-full" />
      </div>
    )
  }

  const handleAction = () => {
    // Redirect to login if they try to interact
    router.push("/auth/login")
  }

  const promptSuggestions = [
    { title: "Initiate data deletion request", subtitle: "Honors the GDPR Right to be Forgotten" },
    { title: "Verify cryptographic proof of deletion", subtitle: "Validate Merkle inclusion proofs & signatures" },
    { title: "Check system security & privacy leakages", subtitle: "Membership Inference Attacks & DP estimates" },
    { title: "View tamper-evident audit log events", subtitle: "Verify hash chain anchoring integrity" },
  ]

  return (
    <div className="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)] flex flex-col font-sans">
      
      {/* Top Navbar */}
      <header className="h-[60px] border-b border-[var(--border-subtle)] flex items-center justify-between px-6 bg-[var(--bg-app)]/90 backdrop-blur sticky top-0 z-20">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-[var(--brand)] text-xl font-bold">⊗</span>
          <span className="font-semibold text-[15px] tracking-wide text-[var(--text-primary)]">VeriUnlearn</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link href="/auth/login">
            <button className="px-3.5 py-1.5 hover:bg-[var(--bg-hover)] rounded-lg text-sm font-medium text-[var(--text-secondary)] transition-all cursor-pointer">
              Log In
            </button>
          </Link>
          <Link href="/auth/register">
            <button className="px-3.5 py-1.5 bg-[var(--brand)] hover:bg-[var(--brand-strong)] text-[var(--text-on-brand)] rounded-lg text-sm font-semibold transition-all cursor-pointer">
              Sign Up
            </button>
          </Link>
        </div>
      </header>

      {/* Hero / Landing Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 max-w-2xl mx-auto w-full space-y-12 pb-24">
        
        {/* Logo and Greeting */}
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="h-16 w-16 rounded-full bg-[var(--brand)] flex items-center justify-center text-[var(--text-on-brand)] text-2xl font-bold shadow-lg">
            ⊗
          </div>
          <h1 className="text-[32px] font-bold text-[var(--text-primary)] tracking-tight">
            Welcome to VeriUnlearn
          </h1>
          <p className="text-[var(--text-secondary)] text-sm max-w-md leading-relaxed">
            Verify machine unlearning compliance dynamically. Generate mathematical proofs that confirm your training data is 100% removed.
          </p>
        </div>

        {/* Central Chat Input Container */}
        <div className="w-full space-y-3">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              handleAction()
            }}
            className="relative bg-[var(--bg-surface)] border border-[var(--border-default)] hover:border-[var(--border-strong)] rounded-2xl p-1.5 pr-3 shadow-[var(--shadow-lg)] transition-all"
          >
            <div className="flex items-center">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask anything about machine unlearning..."
                className="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-tertiary)] focus:outline-none py-2.5 px-4"
              />
              <button
                type="submit"
                className="p-2.5 bg-[var(--brand)] text-[var(--text-on-brand)] hover:bg-[var(--brand-strong)] rounded-xl transition-all cursor-pointer"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </form>
          <p className="text-[11px] text-[var(--text-tertiary)] text-center">
            Sign up to run unlearning pipelines, check Merkle trees, and verify zk-SNARK deletion proofs.
          </p>
        </div>

        {/* Grid of PromptSuggestions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
          {promptSuggestions.map((suggestion) => (
            <button
              key={suggestion.title}
              onClick={handleAction}
              className="p-4 bg-[var(--bg-surface)] hover:bg-[var(--bg-hover)] border border-[var(--border-default)] hover:border-[var(--border-strong)] rounded-xl text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-[var(--text-primary)] group-hover:text-[var(--brand)] transition-colors">
                  {suggestion.title}
                </p>
                <ArrowRight className="h-4 w-4 text-[var(--text-tertiary)] group-hover:text-[var(--brand)] group-hover:translate-x-1 transition-all" />
              </div>
              <p className="text-xs text-[var(--text-secondary)] mt-1">
                {suggestion.subtitle}
              </p>
            </button>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]/30 shrink-0 text-center text-xs text-[var(--text-tertiary)]">
        <div className="flex justify-center gap-4 mb-2">
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5 text-[var(--brand)]" />
            GDPR Compliant
          </span>
          <span className="flex items-center gap-1">
            <Zap className="h-3.5 w-3.5 text-[var(--brand)]" />
            Cryptographic Guarantee
          </span>
        </div>
        <p>© 2026 VeriUnlearn. All rights reserved.</p>
      </footer>
    </div>
  )
}
