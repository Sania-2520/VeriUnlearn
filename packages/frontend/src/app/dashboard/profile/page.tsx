"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuthStore } from "@/lib/store/auth-store"
import { MFASetupForm } from "@/components/auth/mfa-setup-form"
import * as authApi from "@/lib/api/auth"

export default function ProfilePage() {
  const { user, updateUser } = useAuthStore()
  const [fullName, setFullName] = useState(user?.full_name || "")
  const [updating, setUpdating] = useState(false)
  const [updateError, setUpdateError] = useState("")
  const [updateSuccess, setUpdateSuccess] = useState(false)

  const [showMFA, setShowMFA] = useState(false)

  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [changingPw, setChangingPw] = useState(false)
  const [pwError, setPwError] = useState("")
  const [pwSuccess, setPwSuccess] = useState(false)

  const [mfaDisableCode, setMfaDisableCode] = useState("")
  const [disablingMFA, setDisablingMFA] = useState(false)
  const [mfaDisableError, setMfaDisableError] = useState("")

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setUpdating(true)
    setUpdateError("")
    setUpdateSuccess(false)
    try {
      const updated = await authApi.updateProfile({ full_name: fullName })
      updateUser(updated)
      setUpdateSuccess(true)
    } catch (err: unknown) {
      setUpdateError(err instanceof Error ? err.message : "Update failed")
    } finally {
      setUpdating(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwError("")
    setPwSuccess(false)
    if (newPassword !== confirmPassword) {
      setPwError("Passwords do not match")
      return
    }
    setChangingPw(true)
    try {
      await authApi.changePassword(currentPassword, newPassword)
      setPwSuccess(true)
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
    } catch (err: unknown) {
      setPwError(err instanceof Error ? err.message : "Password change failed")
    } finally {
      setChangingPw(false)
    }
  }

  const handleDisableMFA = async (e: React.FormEvent) => {
    e.preventDefault()
    setMfaDisableError("")
    setDisablingMFA(true)
    try {
      await authApi.disableMFA(mfaDisableCode)
      updateUser({ mfa_enabled: false })
      setMfaDisableCode("")
    } catch (err: unknown) {
      setMfaDisableError(err instanceof Error ? err.message : "Failed to disable MFA")
    } finally {
      setDisablingMFA(false)
    }
  }

  if (!user) return null

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">Profile Settings</h1>

      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Profile Information</h3>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleUpdateProfile} className="space-y-4 max-w-md">
            <Input
              id="email"
              label="Email"
              value={user.email}
              disabled
            />
            <Input
              id="fullName"
              label="Full Name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
            />
            {updateError && <p className="text-sm text-[var(--danger)]">{updateError}</p>}
            {updateSuccess && <p className="text-sm text-[var(--success)]">Profile updated successfully</p>}
            <Button type="submit" loading={updating}>Save Changes</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Two-Factor Authentication</h3>
        </CardHeader>
        <CardContent>
          {user.mfa_enabled ? (
            <div className="space-y-4 max-w-md">
              <p className="text-sm text-[var(--success)] font-medium">MFA is enabled</p>
              <form onSubmit={handleDisableMFA} className="space-y-3">
                <Input
                  id="disable-mfa-code"
                  label="Authenticator Code to Disable"
                  value={mfaDisableCode}
                  onChange={(e) => setMfaDisableCode(e.target.value)}
                  placeholder="000000"
                  required
                />
                {mfaDisableError && <p className="text-sm text-[var(--danger)]">{mfaDisableError}</p>}
                <Button type="submit" variant="danger" loading={disablingMFA}>
                  Disable MFA
                </Button>
              </form>
            </div>
          ) : showMFA ? (
            <MFASetupForm
              onComplete={() => {
                setShowMFA(false)
                updateUser({ mfa_enabled: true })
              }}
              onCancel={() => setShowMFA(false)}
            />
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-[var(--text-secondary)]">Add an extra layer of security to your account</p>
              <Button onClick={() => setShowMFA(true)}>Set Up MFA</Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <h3 className="text-lg font-semibold">Change Password</h3>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
            <Input
              id="current-password"
              label="Current Password"
              type="password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
              autoComplete="current-password"
            />
            <Input
              id="new-password"
              label="New Password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
            <Input
              id="confirm-password"
              label="Confirm New Password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              autoComplete="new-password"
            />
            {pwError && <p className="text-sm text-[var(--danger)]">{pwError}</p>}
            {pwSuccess && <p className="text-sm text-[var(--success)]">Password changed successfully</p>}
            <Button type="submit" loading={changingPw}>Change Password</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
