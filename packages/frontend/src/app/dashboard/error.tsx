"use client";

import { useEffect } from "react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Dashboard error:", error);
  }, [error]);

  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <div className="max-w-md rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] p-8 text-center">
        <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Dashboard Error</h2>
        <p className="text-[var(--text-secondary)] mb-4">{error.message || "Failed to load dashboard"}</p>
        <button
          onClick={reset}
          className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-medium text-[var(--text-on-brand)] hover:bg-[var(--brand-strong)] transition-colors cursor-pointer"
        >
          Retry
        </button>
      </div>
    </div>
  );
}
