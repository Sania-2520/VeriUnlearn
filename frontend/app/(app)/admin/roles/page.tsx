"use client";

import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Shield, Check } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/progress";
import { roleLabel } from "@/lib/rbac";

interface Matrix {
  roles: string[];
  permissions: string[];
  matrix: { role: string; permissions: string[] }[];
}

export default function RolesPage() {
  const matrix = useQuery<Matrix>({
    queryKey: ["admin-roles"],
    queryFn: () => api.get("/api/v1/admin/roles"),
  });

  if (matrix.isLoading || !matrix.data) {
    return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;
  }

  const byRole = Object.fromEntries(matrix.data.matrix.map((r) => [r.role, new Set(r.permissions)]));
  const roles = matrix.data.roles;
  const permissions = matrix.data.permissions;

  return (
    <div className="space-y-6">
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl font-bold tracking-tight">Role-based access control</h1>
        <p className="mt-1 text-sm text-slate-500">
          Permission matrix enforced at the API layer (<code className="mono rounded bg-slate-800 px-1 py-0.5 text-[11px]">require_permission</code>) and mirrored in the UI.
        </p>
      </motion.div>

      <Card>
        <CardHeader>
          <CardTitle>
            <span className="flex items-center gap-2"><Shield className="h-4 w-4 text-cyan-400" /> Role × permission matrix</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800">
                <th className="py-2 pr-4 text-[10px] uppercase tracking-wider text-slate-500">Permission</th>
                {roles.map((r) => (
                  <th key={r} className="px-2 py-2 text-center text-[10px] uppercase tracking-wider text-slate-500">
                    {roleLabel(r)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {permissions.map((p) => (
                <tr key={p} className="border-b border-slate-800/50">
                  <td className="mono py-1.5 pr-4 text-slate-300">{p}</td>
                  {roles.map((r) => (
                    <td key={r} className="px-2 py-1.5 text-center">
                      {byRole[r]?.has(p) ? (
                        <Check className="mx-auto h-3.5 w-3.5 text-emerald-400" />
                      ) : (
                        <span className="text-slate-700">·</span>
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-3">
        {roles.map((r) => (
          <motion.div key={r} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Badge tone={r === "admin" ? "rose" : r === "viewer" ? "slate" : "cyan"}>{roleLabel(r)}</Badge>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-slate-500">{byRole[r]?.size ?? 0} permissions</p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {[...(byRole[r] ?? [])].sort().map((p) => (
                    <span key={p} className="mono rounded bg-slate-800/70 px-1.5 py-0.5 text-[10px] text-slate-400">{p}</span>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
