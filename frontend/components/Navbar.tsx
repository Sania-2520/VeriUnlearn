"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "../store/auth";

const NAV_ITEMS = [
  { href: "/workspace", label: "Workspace" },
  { href: "/datasets", label: "Datasets" },
  { href: "/training", label: "Training" },
  { href: "/models", label: "Models" },
  { href: "/unlearning", label: "Unlearning" },
  { href: "/verification", label: "Verification" },
  { href: "/documents", label: "Documents" },
  { href: "/dashboard", label: "Dashboard" },
];

const SECONDARY_ITEMS = [
  { href: "/operations", label: "Operations" },
  { href: "/lineage", label: "Lineage" },
  { href: "/benchmarks", label: "Benchmarks" },
  { href: "/privacy", label: "Privacy" },
  { href: "/compliance", label: "Compliance" },
  { href: "/research", label: "Research" },
  { href: "/research/algorithms", label: "Algorithms" },
  { href: "/research/leaderboards", label: "Leaderboards" },
  { href: "/research/attacks", label: "Attacks" },
  { href: "/research/comparisons", label: "Compare" },
  { href: "/research/reports", label: "Reports" },
];

export default function Navbar() {
  const { user, logout } = useAuthStore();
  const pathname = usePathname();

  const isActive = (href: string) => pathname === href;

  return (
    <nav className="border-b border-gray-200 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          <div className="flex items-center space-x-6">
            <Link href="/workspace" className="text-sm font-semibold text-gray-900">
              VeriUnlearn
            </Link>
            <div className="flex space-x-1">
              {NAV_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`text-sm px-3 py-1.5 rounded-md transition-colors ${
                    isActive(item.href)
                      ? "bg-primary-50 text-primary-700 font-medium"
                      : "text-gray-500 hover:text-gray-700 hover:bg-gray-50"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
              {SECONDARY_ITEMS.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`text-sm px-3 py-1.5 rounded-md transition-colors ${
                    isActive(item.href)
                      ? "bg-primary-50 text-primary-700 font-medium"
                      : "text-gray-400 hover:text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  {item.label}
                </Link>
              ))}
              {user?.role === "admin" && (
                <Link
                  href="/admin"
                  className={`text-sm px-3 py-1.5 rounded-md transition-colors ${
                    isActive("/admin")
                      ? "bg-primary-50 text-primary-700 font-medium"
                      : "text-gray-400 hover:text-gray-600 hover:bg-gray-50"
                  }`}
                >
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
