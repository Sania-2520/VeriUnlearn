"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { useAuthStore } from "@/lib/store/auth-store"

export default function MFAVerifyPage() {
  const router = useRouter()
  const { challengeToken, setChallengeToken } = useAuthStore()
  const [code, setCode] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!challengeToken) {
      router.push("/auth/login")
    }
  }, [challengeToken, router])

  if (!challengeToken) {
    return null
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const { verifyMFAChallenge } = await import("@/lib/api/auth")
      const { setTokens } = await import("@/lib/api/client")
      const res = await verifyMFAChallenge({ challenge_token: challengeToken, code })
      setTokens(res.access_token, res.refresh_token)
      useAuthStore.getState().setAccessToken(res.access_token)
      setChallengeToken(null)
      await useAuthStore.getState().loadUser()
      router.push("/dashboard")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <h2 className="text-2xl font-bold text-center">Two-Factor Authentication</h2>
          <p className="text-sm text-gray-500 text-center mt-1">
            Enter the code from your authenticator app
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              id="mfa-code"
              label="Authentication Code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="000000"
              required
              autoFocus
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" loading={loading} className="w-full">
              Verify
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={() => router.push("/auth/login")}>
              Back to login
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
