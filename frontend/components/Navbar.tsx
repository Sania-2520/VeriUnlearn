"use client";

import Link from "next/link";
import { useAuthStore } from "../store/auth";

export default function Navbar() {
  const { user, logout } = useAuthStore();

  return (
    <nav className="border-b border-gray-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          <div className="flex items-center space-x-8">
            <Link href="/workspace" className="text-sm font-semibold text-gray-900">
              VeriUnlearn
            </Link>
            <div className="flex space-x-4">
              <Link href="/workspace" className="text-sm text-gray-500 hover:text-gray-700">
                Workspace
              </Link>
              <Link href="/documents" className="text-sm text-gray-500 hover:text-gray-700">
                Documents
              </Link>
              <Link href="/dashboard" className="text-sm text-gray-500 hover:text-gray-700">
                Dashboard
              </Link>
              <Link href="/lineage" className="text-sm text-gray-500 hover:text-gray-700">
                Lineage
              </Link>
              <Link href="/benchmarks" className="text-sm text-gray-500 hover:text-gray-700">
                Benchmarks
              </Link>
              <Link href="/privacy" className="text-sm text-gray-500 hover:text-gray-700">
                Privacy
              </Link>
              <Link href="/compliance" className="text-sm text-gray-500 hover:text-gray-700">
                Compliance
              </Link>
              {user?.role === "admin" && (
                <Link href="/admin" className="text-sm text-gray-500 hover:text-gray-700">
                  Admin
                </Link>
              )}
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/settings" className="text-sm text-gray-400 hover:text-gray-600">
              {user?.username}
            </Link>
            <button
              onClick={logout}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Sign Out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
