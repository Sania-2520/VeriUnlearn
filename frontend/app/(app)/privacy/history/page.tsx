"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { motion } from "framer-motion";
import { History, Search, SlidersHorizontal } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/progress";
import { timeAgo } from "@/lib/utils";

interface HistoryEntry {
  id: string;
  query: string;
  filters: Record<string, string> | null;
  result_count: number;
  created_at: string | null;
}

export default function SearchHistoryPage() {
  const history = useQuery<{ history: HistoryEntry[] }>({
    queryKey: ["search-history"],
    queryFn: () => api.get("/api/v1/privacy/history"),
  });

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Search History</h1>
        <p className="mt-1 text-sm text-slate-500">
          Every identity lookup you have run against the Privacy Auditor — auditable and replayable.
        </p>
      </motion.div>

      <Card>
        <CardHeader>
          <CardTitle>Recent identity searches</CardTitle>
          <History className="h-5 w-5 text-cyan-400" />
        </CardHeader>
        <CardContent>
          {history.isLoading ? (
            <div className="flex justify-center py-10">
              <Spinner />
            </div>
          ) : history.data && history.data.history.length > 0 ? (
            <div className="space-y-3">
              {history.data.history.map((h, i) => (
                <motion.div
                  key={h.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/40 px-4 py-3"
                >
                  <Search className="h-4 w-4 shrink-0 text-cyan-400" />
                  <span className="mono min-w-0 flex-1 truncate text-sm text-slate-200">
                    {h.query || (
                      <span className="text-slate-500">
                        structured: {h.filters ? Object.entries(h.filters).map(([k, v]) => `${k}=${v}`).join(", ") : "—"}
                      </span>
                    )}
                  </span>
                  {h.filters && Object.keys(h.filters).length > 0 && (
                    <Badge tone="violet">
                      <SlidersHorizontal className="mr-1 h-3 w-3" /> filtered
                    </Badge>
                  )}
                  <Badge tone={h.result_count > 0 ? "emerald" : "slate"}>{h.result_count} matches</Badge>
                  <span className="text-xs text-slate-500">{timeAgo(h.created_at)}</span>
                  <Link href={`/privacy?q=${encodeURIComponent(h.query || "")}`}>
                    <Button variant="ghost" size="sm">Re-run</Button>
                  </Link>
                </motion.div>
              ))}
            </div>
          ) : (
            <p className="py-10 text-center text-sm text-slate-500">
              No searches yet — run an identity search from the{" "}
              <Link href="/privacy" className="text-cyan-400 hover:underline">
                Privacy Auditor
              </Link>
              .
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
