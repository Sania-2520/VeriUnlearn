"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import * as authApi from "@/lib/api/auth"
import { useAuthStore } from "@/lib/store/auth-store"

interface MFASetupFormProps {
  onComplete: () => void
  onCancel: () => void
}

export function MFASetupForm({ onComplete, onCancel }: MFASetupFormProps) {
  const { updateUser } = useAuthStore()
  const [step, setStep] = useState<"password" | "setup" | "verify">("password")
  const [password, setPassword] = useState("")
  const [secret, setSecret] = useState("")
  const [provisioningUri, setProvisioningUri] = useState("")
  const [code, setCode] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      const result = await authApi.setupMFA(password)
      setSecret(result.secret)
      setProvisioningUri(result.provisioning_uri)
      setStep("setup")
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Verification failed")
    } finally {
      setLoading(false)
    }
  }

  const handleEnable = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)
    try {
      await authApi.enableMFA(secret, code)
      updateUser({ mfa_enabled: true })
      onComplete()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to enable MFA")
    } finally {
      setLoading(false)
    }
  }

  if (step === "setup") {
    return (
      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Set Up Authenticator</h3>
          <p className="text-sm text-gray-500">
            Scan the QR code or enter the secret key in your authenticator app
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          {provisioningUri && (
            <div className="flex justify-center">
              <img
                src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(provisioningUri)}`}
                alt="QR Code"
                className="rounded-lg border"
              />
            </div>
          )}
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Secret Key</p>
            <code className="text-sm font-mono break-all">{secret}</code>
          </div>

          <form onSubmit={handleEnable} className="space-y-3">
            <Input
              id="mfa-code"
              label="Verification Code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="000000"
              required
              autoFocus
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-2">
              <Button type="submit" loading={loading}>
                Enable MFA
              </Button>
              <Button type="button" variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <h3 className="text-lg font-semibold">Enable Two-Factor Authentication</h3>
        <p className="text-sm text-gray-500">
          Verify your password to set up MFA
        </p>
      </CardHeader>
      <CardContent>
        <form onSubmit={handlePasswordSubmit} className="space-y-3">
          <Input
            id="mfa-password"
            label="Current Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoFocus
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <div className="flex gap-2">
            <Button type="submit" loading={loading}>
              Continue
            </Button>
            <Button type="button" variant="outline" onClick={onCancel}>
              Cancel
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
