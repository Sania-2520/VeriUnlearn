"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useAuthStore } from "@/lib/store/auth-store"
import {
  Brain,
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
      <div className="min-h-screen flex items-center justify-center bg-[#212121]">
        <div className="animate-spin h-8 w-8 border-4 border-emerald-500 border-t-transparent rounded-full" />
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
    <div className="min-h-screen bg-[#212121] text-gray-200 flex flex-col font-sans">
      
      {/* Top Navbar */}
      <header className="h-[60px] border-b border-[#2f2f2f]/30 flex items-center justify-between px-6 bg-[#212121]/90 backdrop-blur sticky top-0 z-20">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-emerald-500 text-xl font-bold">⊗</span>
          <span className="font-semibold text-[15px] tracking-wide text-white">VeriUnlearn</span>
        </Link>
        <div className="flex items-center gap-3">
          <Link href="/auth/login">
            <button className="px-3.5 py-1.5 hover:bg-[#2f2f2f] rounded-lg text-sm font-medium text-gray-200 transition-all cursor-pointer">
              Log In
            </button>
          </Link>
          <Link href="/auth/register">
            <button className="px-3.5 py-1.5 bg-white hover:bg-gray-200 text-[#171717] rounded-lg text-sm font-semibold transition-all cursor-pointer">
              Sign Up
            </button>
          </Link>
        </div>
      </header>

      {/* Hero / Landing Section */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 max-w-2xl mx-auto w-full space-y-12 pb-24">
        
        {/* Logo and Greeting */}
        <div className="flex flex-col items-center text-center space-y-4">
          <div className="h-16 w-16 rounded-full bg-emerald-700/80 flex items-center justify-center text-white text-2xl font-bold shadow-lg">
            ⊗
          </div>
          <h1 className="text-[32px] font-bold text-white tracking-tight">
            Welcome to VeriUnlearn
          </h1>
          <p className="text-gray-400 text-sm max-w-md leading-relaxed">
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
            className="relative bg-[#171717] border border-[#2f2f2f] hover:border-gray-500 rounded-2xl p-1.5 pr-3 shadow-2xl transition-all"
          >
            <div className="flex items-center">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask anything about machine unlearning..."
                className="flex-1 bg-transparent text-sm text-white placeholder-gray-500 focus:outline-none py-2.5 px-4"
              />
              <button
                type="submit"
                className="p-2.5 bg-white text-[#171717] hover:bg-gray-200 rounded-xl transition-all cursor-pointer"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </form>
          <p className="text-[11px] text-gray-500 text-center">
            Sign up to run unlearning pipelines, check Merkle trees, and verify zk-SNARK deletion proofs.
          </p>
        </div>

        {/* Grid of PromptSuggestions */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
          {promptSuggestions.map((suggestion) => (
            <button
              key={suggestion.title}
              onClick={handleAction}
              className="p-4 bg-[#171717]/30 hover:bg-[#2f2f2f]/40 border border-[#2f2f2f]/60 hover:border-gray-500 rounded-xl text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-gray-200 group-hover:text-white transition-colors">
                  {suggestion.title}
                </p>
                <ArrowRight className="h-4 w-4 text-gray-500 group-hover:text-white group-hover:translate-x-1 transition-all" />
              </div>
              <p className="text-xs text-gray-400 mt-1">
                {suggestion.subtitle}
              </p>
            </button>
          ))}
        </div>
      </main>

      {/* Footer */}
      <footer className="py-6 border-t border-[#2f2f2f]/20 bg-[#171717]/30 shrink-0 text-center text-xs text-gray-500">
        <div className="flex justify-center gap-4 mb-2">
          <span className="flex items-center gap-1">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
            GDPR Compliant
          </span>
          <span className="flex items-center gap-1">
            <Zap className="h-3.5 w-3.5 text-emerald-600" />
            Cryptographic Guarantee
          </span>
        </div>
        <p>© 2026 VeriUnlearn. All rights reserved.</p>
      </footer>
    </div>
  )
}
