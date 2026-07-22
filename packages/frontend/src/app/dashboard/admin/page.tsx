"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import * as adminApi from "@/lib/api/admin"

export default function AdminPage() {
  const [userCount, setUserCount] = useState<number | null>(null)
  const [jobCount, setJobCount] = useState<number | null>(null)

  useEffect(() => {
    adminApi.listUsers({ page_size: 1 }).then((res) => {
      setUserCount(res.meta.total)
    }).catch((err) => console.error("Failed to fetch user count:", err))
  }, [])

  useEffect(() => {
    adminApi.listJobs({ page_size: 1 }).then((res) => {
      setJobCount(res.meta.total)
    }).catch((err) => console.error("Failed to fetch job count:", err))
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Admin</h1>
        <p className="text-sm text-[var(--text-secondary)] mt-1">System administration and management</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link href="/dashboard/admin/users">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <p className="text-sm text-[var(--text-secondary)]">Users</p>
              <p className="text-2xl font-bold mt-1">{userCount !== null ? userCount : <span className="animate-pulse">—</span>}</p>
              <p className="text-xs text-[var(--accent)] mt-2">Manage roles and permissions →</p>
            </CardContent>
          </Card>
        </Link>

        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-[var(--text-secondary)]">Background Jobs</p>
            <p className="text-2xl font-bold mt-1">{jobCount !== null ? jobCount : <span className="animate-pulse">—</span>}</p>
            <p className="text-xs text-[var(--text-tertiary)] mt-2">Unlearning and verification jobs</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
