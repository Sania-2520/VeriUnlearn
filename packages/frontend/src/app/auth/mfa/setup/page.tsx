"use client"

import { useRouter } from "next/navigation"
import { MFASetupForm } from "@/components/auth/mfa-setup-form"

export default function MFASetupPage() {
  const router = useRouter()

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-lg">
        <MFASetupForm
          onComplete={() => router.push("/dashboard")}
          onCancel={() => router.push("/dashboard")}
        />
      </div>
    </div>
  )
}
