"use client"

import { LoginForm } from "@/components/auth/login-form"

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">VeriUnlearn</h1>
          <p className="text-sm text-gray-500 mt-1">Verifiable Machine Unlearning Platform</p>
        </div>
        <LoginForm />
      </div>
    </div>
  )
}
