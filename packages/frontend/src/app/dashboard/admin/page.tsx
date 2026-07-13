"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import * as adminApi from "@/lib/api/admin"

export default function AdminPage() {
  const [userCount, setUserCount] = useState(0)
  const [jobCount, setJobCount] = useState(0)

  useEffect(() => {
    adminApi.listUsers({ page_size: 1 }).then((res) => {
      setUserCount(res.meta.total)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    adminApi.listJobs({ page_size: 1 }).then((res) => {
      setJobCount(res.meta.total)
    }).catch(() => {})
  }, [])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Admin</h1>
        <p className="text-sm text-gray-500 mt-1">System administration and management</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link href="/dashboard/admin/users">
          <Card className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="pt-6">
              <p className="text-sm text-gray-500">Users</p>
              <p className="text-2xl font-bold mt-1">{userCount}</p>
              <p className="text-xs text-blue-600 mt-2">Manage roles and permissions →</p>
            </CardContent>
          </Card>
        </Link>

        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-gray-500">Background Jobs</p>
            <p className="text-2xl font-bold mt-1">{jobCount}</p>
            <p className="text-xs text-gray-400 mt-2">Unlearning and verification jobs</p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
