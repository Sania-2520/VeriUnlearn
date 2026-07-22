"use client";

import { useEffect } from "react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Application error:", error);
  }, [error]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--bg-app)]">
      <div className="max-w-md rounded-lg bg-[var(--bg-surface)] border border-[var(--border-default)] p-8 text-center">
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-2">Something went wrong</h2>
        <p className="text-[var(--text-secondary)] mb-4">
          An unexpected error occurred. Please try again.
        </p>
        <button
          onClick={reset}
          className="rounded-lg bg-[var(--brand)] px-4 py-2 text-sm font-medium text-[var(--text-on-brand)] hover:bg-[var(--brand-strong)] transition-colors cursor-pointer"
        >
          Try Again
        </button>
      </div>
    </div>
  );
}
