"use client"

import { ApiKeyManager } from "@/components/auth/api-key-manager"

export default function ApiKeysPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>
        <p className="text-sm text-gray-500 mt-1">Manage your API keys for programmatic access</p>
      </div>
      <ApiKeyManager />
    </div>
  )
}
