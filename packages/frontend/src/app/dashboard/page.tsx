"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { useAuthStore } from "@/lib/store/auth-store"
import { useRouter } from "next/navigation"
import * as authApi from "@/lib/api/auth"
import * as unlearningApi from "@/lib/api/unlearning"

export default function DashboardPage() {
  const { user } = useAuthStore()
  const router = useRouter()
  const [eventCount, setEventCount] = useState(0)
  const [requestCount, setRequestCount] = useState(0)
  const [pendingCount, setPendingCount] = useState(0)
  const [completedCount, setCompletedCount] = useState(0)

  useEffect(() => {
    authApi.getAuditEvents({ page_size: 1 }).then((res) => {
      setEventCount(res.meta.total)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    unlearningApi.listRequests({ page_size: 1 }).then((res) => {
      setRequestCount(res.meta.total)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    unlearningApi.listRequests({ page_size: 1, status: "pending" }).then((res) => {
      setPendingCount(res.meta.total)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    unlearningApi.listRequests({ page_size: 1, status: "completed" }).then((res) => {
      setCompletedCount(res.meta.total)
    }).catch(() => {})
  }, [])

  if (!user) return null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Overview</h1>
        <p className="text-sm text-gray-500 mt-1">Welcome back, {user.full_name}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">Account Status</p>
            <p className="text-2xl font-bold mt-1">{user.is_email_verified ? "Verified" : "Unverified"}</p>
            <span className={`text-xs px-2 py-0.5 rounded-full mt-2 inline-block ${user.mfa_enabled ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}`}>
              {user.mfa_enabled ? "MFA Enabled" : "MFA Disabled"}
            </span>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">Role</p>
            <p className="text-2xl font-bold mt-1 capitalize">{user.role}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">Audit Events</p>
            <p className="text-2xl font-bold mt-1">{eventCount}</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">Unlearning Requests</p>
            <p className="text-2xl font-bold mt-1">{requestCount}</p>
          </CardContent>
        </Card>
      </div>

      {/* Unlearning Stats */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900">Deletion Requests</h3>
            <Link href="/dashboard/unlearning">
              <Button variant="ghost" size="sm">View All</Button>
            </Link>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-2xl font-bold text-blue-700">{pendingCount}</p>
              <p className="text-xs text-blue-600 mt-1">Pending</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <p className="text-2xl font-bold text-green-700">{completedCount}</p>
              <p className="text-xs text-green-600 mt-1">Completed</p>
            </div>
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-700">{requestCount}</p>
              <p className="text-xs text-gray-600 mt-1">Total</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {!user.mfa_enabled && (
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="flex items-center justify-between py-4">
            <div>
              <p className="font-medium text-amber-800">Security Recommendation</p>
              <p className="text-sm text-amber-600">Enable two-factor authentication to protect your account</p>
            </div>
            <Button onClick={() => router.push("/auth/mfa/setup")}>Set Up MFA</Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
