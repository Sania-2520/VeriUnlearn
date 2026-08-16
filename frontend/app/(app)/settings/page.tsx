"use client";

import { useQuery } from "@tanstack/react-query";
import { UserCircle2, ShieldCheck, KeyRound, Server } from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useAuth } from "@/lib/auth";

export default function SettingsPage() {
  const { user } = useAuth();
  const { data: users } = useQuery<{ users: { id: string; email: string; full_name: string; role: string }[] }>({
    queryKey: ["admin-users"],
    queryFn: () => api.get("/api/v1/admin/users"),
    enabled: user?.role === "admin",
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">Account, roles and platform configuration.</p>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><UserCircle2 className="h-4 w-4 text-cyan-400" /> Profile</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Row label="Name" value={user?.full_name ?? "—"} />
              <Row label="Email" value={user?.email ?? "—"} />
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-400">Role</span>
                <Badge tone="violet" className="capitalize">{user?.role}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><KeyRound className="h-4 w-4 text-amber-400" /> Credentials</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-400">
              JWT session with role-based access. Passwords are bcrypt-hashed; PII fields at rest are
              AES-256-GCM encrypted; certificates are RSA-signed.
            </p>
            <div className="mono mt-3 rounded-lg border border-slate-800 bg-slate-900/50 p-3 text-xs text-slate-500">
              JWT · HS256 · bcrypt · AES-GCM · RSA-PKCS1v15
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Server className="h-4 w-4 text-emerald-400" /> Runtime</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <Row label="API" value="FastAPI /api/v1" />
              <Row label="Docs" value="/docs (OpenAPI)" />
              <Row label="ML core" value="scikit-learn + SISA" />
              <Row label="Vector store" value="in-memory (Qdrant optional)" />
            </div>
          </CardContent>
        </Card>
      </div>

      {user?.role === "admin" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-rose-400" /> Admin — Users</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(users?.users ?? []).map((u) => (
                <div key={u.id} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-2.5 text-sm">
                  <div>
                    <p className="font-medium text-slate-100">{u.full_name}</p>
                    <p className="mono text-xs text-slate-500">{u.email}</p>
                  </div>
                  <Badge tone={u.role === "admin" ? "rose" : u.role === "auditor" ? "violet" : "cyan"} className="capitalize">{u.role}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-slate-400">{label}</span>
      <span className="mono text-xs text-cyan-300">{value}</span>
    </div>
  );
}
