"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { useAuthStore } from "@/lib/store/auth-store"

export function LoginForm() {
  const router = useRouter()
  const { login, challengeToken, setChallengeToken } = useAuthStore()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [mfaCode, setMfaCode] = useState("")
  const [mfaLoading, setMfaLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await login(email, password)
      if (!useAuthStore.getState().challengeToken) {
        router.push("/dashboard")
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed")
    } finally {
      setLoading(false)
    }
  }

  const handleMFAVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!challengeToken) return
    setError("")
    setMfaLoading(true)
    try {
      const { verifyMFAChallenge } = await import("@/lib/api/auth")
      const res = await verifyMFAChallenge({ challenge_token: challengeToken, code: mfaCode })
      const { setTokens } = await import("@/lib/api/client")
      setTokens(res.access_token, res.refresh_token)
      useAuthStore.getState().setAccessToken(res.access_token)
      setChallengeToken(null)
      await useAuthStore.getState().loadUser()
      router.push("/dashboard")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "MFA verification failed")
    } finally {
      setMfaLoading(false)
    }
  }

  if (challengeToken) {
    return (
      <Card className="w-full max-w-md mx-auto">
        <CardHeader>
          <h2 className="text-2xl font-bold text-center">Two-Factor Authentication</h2>
          <p className="text-sm text-gray-500 text-center mt-1">
            Enter the code from your authenticator app
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleMFAVerify} className="space-y-4">
            <Input
              id="mfa-code"
              label="Authentication Code"
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              placeholder="000000"
              required
              autoFocus
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" loading={mfaLoading} className="w-full">
              Verify
            </Button>
          </form>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <h2 className="text-2xl font-bold text-center">Sign In</h2>
        <p className="text-sm text-gray-500 text-center mt-1">
          Welcome back to VeriUnlearn
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            id="email"
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            autoComplete="email"
          />
          <Input
            id="password"
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter your password"
            required
            autoComplete="current-password"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button type="submit" loading={loading} className="w-full">
            Sign In
          </Button>
        </form>

        <div className="mt-4 text-center text-sm">
          <a href="/auth/forgot-password" className="text-blue-600 hover:text-blue-800">
            Forgot password?
          </a>
        </div>

        <div className="mt-6 text-center text-sm text-gray-500">
          Don&apos;t have an account?{" "}
          <a href="/auth/register" className="text-blue-600 hover:text-blue-800 font-medium">
            Sign up
          </a>
        </div>
      </CardContent>
    </Card>
  )
}
